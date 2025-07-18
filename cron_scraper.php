<?php
// Exécuter le script Python (nécessite que le serveur autorise exec)
// À adapter selon l'installation Python sur Infomaniak !
exec("python3 /home/clients/88825ac5e5f79e7ac027b682eb1b2848/sites/thegreenpadel.fr/scraper/scraper_full_year.py > /home/clients/88825ac5e5f79e7ac027b682eb1b2848/sites/thegreenpadel.fr/logs/cron.log 2>&1 &");
echo "OK";
?>
