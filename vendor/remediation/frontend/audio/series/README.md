# Mots entendus

48 mots prononcés par la voix française locale Thomas (macOS), débit 155 mots/minute. AAC mono 32 kbit/s ; 329 297 octets au total. Un fichier par mot, mutualisé entre les séries, sans téléchargement de voix à l’usage ni service de synthèse distant.

Préparation : `python3 tools/generer_audio_series.py` sur macOS avec les voix système accessibles. Le script refuse les synthèses vides et conserve les fichiers déjà présents. Changer de profil pour modifier volontairement une voix : les URL du profil existant sont immuables.

Le manifest documente la durée et la taille de chaque fichier. Il faut encore une écoute humaine des prononciations avant une utilisation accompagnée régulière ; ce matériel n’est pas étalonné.
