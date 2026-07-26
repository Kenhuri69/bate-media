# Intégrer les voix dans le jeu

## Principe : le pack est optionnel par construction

`AudioManager.ResolveClip()` (dans `src/core/audio_manager/AudioManager.cs`) charge
paresseusement `res://assets/audio/{clé}.ogg` et **rend `null` si le fichier n'existe pas**.
Le comportement « non critique » est donc déjà celui du moteur : appeler une voix absente
ne lève rien, ne journalise rien de fatal, et le dialogue continue en silence.

Convention retenue :

| élément | valeur |
|---|---|
| chemin | `res://assets/audio/voice/<personnage>/<id>.ogg` |
| clé AudioManager | `voice/<personnage>/<id>` |
| id | `<personnage>_ch<NN>_<II>` — ex. `alice_ch08_02` |

Le `manifest.json` déposé dans chaque dossier relie l'`id` au texte exact de la réplique :
c'est lui qui permet de retrouver le fichier correspondant à une ligne de timeline sans
dépendre d'un ordre implicite.

## Côté C# : une méthode symétrique de PlaySFX

```csharp
/// Joue la voix d'une réplique si le pack de médias est installé ; sans effet sinon.
/// L'immersion est optionnelle : aucune partie ne doit dépendre de la présence d'un .ogg.
public void PlayVoice(string personnage, string id)
{
    var stream = ResolveClip($"voice/{personnage.ToLowerInvariant()}/{id}");
    if (stream == null) return;      // pack absent : on continue en silence
    _voicePlayer.Stream = stream;
    _voicePlayer.Play();
}
```

Un `AudioStreamPlayer` dédié (bus `Voice`) évite que la voix coupe la musique et permet un
réglage de volume séparé — utile puisque certains joueurs voudront les dialogues écrits sans
la voix.

## Côté Dialogic : déclencher au bon moment

Deux approches, selon le degré d'automatisme voulu :

1. **Par signal** — s'abonner au signal Dialogic émis à chaque ligne, en déduire l'`id`
   depuis le personnage et le compteur de répliques du chapitre courant, appeler
   `PlayVoice`. Aucune modification des 98 timelines, mais il faut que le compteur suive
   exactement l'ordre d'extraction (`<perso>_ch<NN>_<II>`, `II` incrémenté par personnage et
   par chapitre).
2. **Par annotation explicite** — ajouter un événement de son dans les timelines aux
   endroits voulus. Plus verbeux, mais robuste au réordonnancement d'une timeline.

La première est cohérente avec l'extraction actuelle et ne demande aucun travail de
réécriture ; la seconde est préférable si les timelines doivent encore beaucoup bouger.

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
