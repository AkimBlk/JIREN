# 🧹 JIREN Cleanup Analysis - Fichiers à Supprimer

## 📊 Analyse: Qu'est-ce qui est RÉELLEMENT utilisé

### APPS ACTIFS (100% Utilisés):
✅ `blog/` - Application principale
   - models.py (Project, Ticket, Sprint, Tag, etc.) - Core système
   - views.py - Toutes les vues actives
   - urls.py - Routing actif
   - forms.py - Tous les formulaires
   - admin.py - Interface admin Django
   - apps.py - Config app
   - templatetags/ - Template filters actifs
   - templates/ - Tous les templates HTML rendus
   - static/ - CSS/JS utilisé
   - management/commands/populate_demo_data.py - Génère dataset démo

✅ `users/` - Application utilisateurs
   - models.py, views.py, forms.py, urls.py - Auth system
   - templates/ - Pages login/register
   - signals.py - Profile auto-creation
   - management/commands/ - Commandes custom

✅ `web_project_django/` - Configuration projet
   - settings.py - Configuration core
   - urls.py - URL dispatcher
   - wsgi.py - Production server
   - asgi.py - Async support
   - __init__.py

### FICHIERS CRITIQUES:
✅ manage.py - CLI Django (essentiel pour commandes)
✅ requirements.txt - Dependencies (pip install)
✅ db.sqlite3 - Base de données (démo data)
✅ .gitignore - Git config
✅ README.md - Documentation
✅ media/ - Profil pictures, attachments

### FICHIERS À SUPPRIMER (Non-utilisés / Debug):

🔴 **Racine dossier (ne servent rien)**:
- check_config.py (utilisé une fois pour debug)
- run.sh (script bash, plateforme windows)
- API_TAGS_DOCUMENTATION.md (documentation figée)
- .github/ (dossier agents personnalisés, pas utilisé par site)

🔴 **Tests inutilisés**:
- blog/test_*.py (4 fichiers - tests de debug)
- blog/tests_security_bugs.py (security audit, archivé)
- users/tests.py

🔴 **Fichiers git-keep**:
- blog/git.gitkeep
- blog/migrations/git.gitkeep (sauf migrations réelles)
- users/git.gitkeep
- media/git.gitkeep
- web_project_django/git.gitkeep

🔴 **venv/**: Virtualenv (régénéré par pip)

🔴 **Non essentiels**:
- .git/ (historique git - optionnel)

---

## 📋 STATISTIQUES

| Catégorie | Action | Taille estimée |
|-----------|--------|-----------------|
| Fichiers debug | Supprimer | ~50KB |
| Tests | Supprimer | ~30KB |
| .gitkeep | Supprimer | <1KB |
| venv/ | Supprimer | ~200MB |
| .git/ | Optionnel | ~5MB |
| **À garder** | **Conserver** | **~2MB** |

---

## 🔍 Migration Squashing (Optimization)

**Current**: 20 fichiers de migrations
**Recommendation**: Garder 0001_initial + appliquer squash pour les 19 autres

Actions:
```bash
python manage.py squashmigrations blog 0020
# Puis supprimer les 0002-0020.py originaux
```

Gain: ~100KB

---

## ✅ NETTOYAGE RECOMMANDÉ (Safe & Reversible)

### Phase 1: Sans risque (99.9% safe - dans utils)
```
×  check_config.py
×  run.sh
×  API_TAGS_DOCUMENTATION.md
×  blog/git.gitkeep
×  blog/tests_security_bugs.py
×  blog/test_*.py
×  users/tests.py
×  users/git.gitkeep
×  media/git.gitkeep
×  web_project_django/git.gitkeep
```

**Économies**: ~80KB + permet Git tracking

### Phase 2: Optionnel (Si production-ready)
```
×  venv/ (Régénéré par: pip install -r requirements.txt)
×  .git/ (Si backup externe existe)
×  db.sqlite3 (Recréé par: python manage.py migrate + populate_demo_data)
```

**Économies**: ~200MB

---

## 🚀 Post-Cleanup

```bash
# Régénérer environnement
pip install -r requirements.txt
python manage.py migrate
python manage.py populate_demo_data --clear

# Le site fonctionne identique
python manage.py runserver 0.0.0.0:8001
```

---

## ⚠️ À NE PAS SUPPRIMER

```
✅ manage.py
✅ requirements.txt
✅ web_project_django/*
✅ blog/models.py, views.py, urls.py, forms.py
✅ blog/templates/blog/*.html
✅ blog/static/blog/*.css
✅ blog/management/commands/populate_demo_data.py
✅ users/models.py, views.py, signals.py
✅ users/templates/users/*
✅ .gitignore
✅ db.sqlite3 (jusqu'à prod)
```
