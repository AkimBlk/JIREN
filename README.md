# project_django jira ekip4
# comment update sur sa branch perso 
**Première fois**

```bash
git checkout -b enzo
git add .
git commit -m "Premier commit sur la branche enzo"
git push -u origin [prenom]
```

**Fois suivantes**

```bash
git checkout enzo
git add .
git commit -m "Mise à jour"
git push origin [prenom]
```

# comment debuter :

### 1. Recuperer le projet
git clone https://github.com/Leviantan07/JIREN-RESURECTION.git <br>
cd JIREN-RESURECTION <br>

# 2.5 Avec environnement virtuel windows :
python -m venv venv <br>
.\venv\Scripts\Activate.ps1 <br>
pip install -r requirements.txt <br>
python manage.py migrate <br>
python3 manage.py makemigrations <br>
python manage.py runserver <br>

# 2.5 Avec environnement virtuel linux :
Installation de venv si necessaire <br>
sudo apt update && sudo apt install python3-venv <br>

python3 -m venv venv
source venv/bin/activate <br>
pip install -r requirements.txt <br>
python3 manage.py migrate <br>
python3 manage.py runserver <br>

# 2.5 Sans venv windows :
pip install -r requirements.txt <br>
python manage.py migrate <br>
python manage.py runserver <br>

# 2.5 Sans venv linux :
pip3 install -r requirements.txt <br>
python3 manage.py migrate <br>
python3 manage.py runserver <br>

# ensuite pour les prochaines fois juste faire python3 manage.py OU bash run.sh (sur linux)

# (calculer pas)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# commande superuser (admin pour la base de donnees):
python manage.py createsuperuser


# comment update sur sa branch perso

**Premiere fois si la branche n'existe pas encore en local**

```bash
git checkout -b enzo
git add .
git commit -m "Premier commit sur la branche enzo"
git push -u origin enzo
```

**Fois suivantes**

```bash
git checkout enzo
git add .
git commit -m "Mise a jour"
git push
```

**Si la branche distante existe deja mais pas en local**

```bash
git fetch origin
git switch -c enzo --track origin/enzo
```

Ensuite :

```bash
git add .
git commit -m "Mise a jour"
git push
```

**Si Git ne sait pas ou push**

Verifier la branche courante et son lien avec le remote :

```bash
git branch -vv
git remote -v
```

Si la branche locale n'est pas liee a la branche distante :

```bash
git push -u origin enzo
```

**Si `git push` est refuse en `non-fast-forward`**

Le remote a des commits que le local n'a pas encore. Recuperer d'abord les changements :

```bash
git fetch origin
git merge origin/enzo
```

S'il y a des conflits, les resoudre, puis :

```bash
git add .
git commit
git push
```

**Si un merge est deja en cours et bloque tout**

Verifier l'etat :

```bash
git status
```

Annuler le merge en cours si necessaire :

```bash
git merge --abort
```

Puis recommencer proprement :

```bash
git fetch origin
git merge origin/enzo
```

**Si `refusing to merge unrelated histories` apparait**

Cela veut dire que les historiques local et distant ne partent pas de la meme base.

```bash
git merge origin/enzo --allow-unrelated-histories
```

Attention : cette commande peut generer beaucoup de conflits. A utiliser seulement si on veut vraiment fusionner les deux historiques.

**Si `Repository not found` ou `Authentication failed` apparait**

Verifier l'URL du depot distant :

```bash
git remote -v
```

Si besoin, remettre la bonne URL :

```bash
git remote set-url origin https://github.com/Leviantan07/JIREN-RESURECTION.git
```

Puis reessayer le push. Si ca bloque encore, il manque probablement les droits GitHub sur le depot ou la branche.
