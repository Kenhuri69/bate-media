# Intégrer les voix dans le jeu

## Principe : le pack est optionnel par construction

`AudioManager.ResolveClip()` (dans `src/core/audio_manager/AudioManager.cs`) charge
paresseusement `res://assets/audio/{clé}.ogg` et **rend `null` si le fichier n'existe pas**.
Le comportement « non critique » est donc déjà celui du moteur : appeler une voix absente
ne lève rien, ne journalise rien de fatal, et le dialogue continue en silence.

Convention retenue :

| élément | valeur |
|---|---|
| chemin | `res://assets/audio/voice/<dossier de voix>/<id>.ogg` |
| clé AudioManager | `voice/<dossier de voix>/<id>` |
| id | `<rôle>_<empreinte du texte>` — ex. `narrator_c03132187d` |

Le `manifest.json` déposé dans chaque dossier relie l'`id` au texte exact de la réplique :
c'est lui qui permet de retrouver le fichier correspondant à une ligne de timeline sans
dépendre d'un ordre implicite.

## Côté C# : une méthode symétrique de PlaySFX

```csharp
/// Joue la voix d'une réplique si le pack de médias est installé ; sans effet sinon.
/// L'immersion est optionnelle : aucune partie ne doit dépendre de la présence d'un .ogg.
public bool PlayVoice(string speaker, string text)
{
    StopVoice();                     // une nouvelle réplique coupe la précédente
    var key = VoiceLines.ClipKey(speaker, text);   // voice/<dossier>/<rôle>_<empreinte>
    if (key == null) return false;
    var stream = ResolveClip(key, cache: false);
    if (stream == null) return false;              // pack absent : on continue en silence
    _voicePlayer.Stream = stream;
    _voicePlayer.Play();
    return true;
}
```

Un `AudioStreamPlayer` dédié (bus `Voice`) évite que la voix coupe la musique et permet un
réglage de volume séparé — utile puisque certains joueurs voudront les dialogues écrits sans
la voix.

## Côté Dialogic : déclencher au bon moment

`scenes/hud/VoiceLine.gd` s'abonne à `Dialogic.Text.about_to_show_text` et appelle `PlayVoice`
à chaque réplique. Aucune des 326 timelines n'est modifiée.

**Le texte utilisé est celui du fichier `.dtl`, pas celui affiché.** C'est le point délicat, et
le seul endroit où la chaîne peut rompre en silence. `about_to_show_text` porte le texte FINAL :
variables substituées, segment courant d'une réplique découpée par `[n+]`, effets appliqués. La
forge, elle, lit le `.dtl`. Hacher l'un pour chercher un clip nommé d'après l'autre ne donnerait
jamais la même empreinte, et le jeu resterait muet sans lever d'erreur. Le nœud lit donc
`event.text`, la propriété que Dialogic remplit depuis la ligne du fichier.

Une version antérieure de ce document proposait de **compter les répliques** au fil du jeu pour
en déduire un rang. C'était faux deux fois : un compteur d'exécution se décale dès qu'une
timeline offre un choix — le joueur n'entend qu'une branche — et un rang de fichier se périme
dès qu'on insère une réplique en amont. L'empreinte du texte supprime les deux problèmes.

## Distribuer le pack aux joueurs

Attention : un build exporté ne contient que les ressources **importées avant l'export**.
Deux voies selon le moment où le pack arrive :

- **Pack présent au moment de l'export** : installer avec `tools/install_pack.py`, ouvrir le
  projet une fois pour que Godot importe les `.ogg`, puis exporter. Les voix sont dans le
  `.pck` du jeu.
- **Pack téléchargé après coup** (le cas d'un vrai DLC d'immersion) : produire un `.pck`
  Godot séparé et le monter à l'exécution avec
  `ProjectSettings.LoadResourcePack("user://bate-voices.pck")`. Les chemins `res://` du pack
  se superposent alors à ceux du jeu, et `ResolveClip` les trouve sans modification.

La seconde voie est celle qui correspond à l'intention de ce dépôt : un pack public,
versionné, installable ou non, sans toucher au binaire du jeu.
