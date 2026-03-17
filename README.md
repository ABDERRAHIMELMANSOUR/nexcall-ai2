# NexCall AI v2.0 — Guide de mise en route

Centre d'appels SaaS avec intelligence artificielle — FastAPI + Ringover + OpenAI

---

## Structure du projet

```
nexcall/
├── main.py                          ← Point d'entrée FastAPI
├── requirements.txt
├── render.yaml                      ← Déploiement Render
├── .env.example  →  .env            ← Configuration (à créer)
├── .python-version                  ← Python 3.11.9
│
├── app/
│   ├── config.py                    ← Paramètres (pydantic-settings)
│   ├── models/
│   │   ├── database.py              ← SQLAlchemy async + init DB
│   │   ├── call.py                  ← Modèle appels
│   │   ├── lead.py                  ← Modèle leads
│   │   ├── campaign.py              ← Modèle campagnes
│   │   ├── ivr.py                   ← Menus IVR + options
│   │   └── agent_config.py         ← Config agent IA
│   ├── routers/
│   │   ├── pages.py                 ← Rendu HTML Jinja2
│   │   ├── calls.py                 ← GET/POST /api/calls
│   │   ├── leads.py                 ← GET/PATCH/DELETE /api/leads
│   │   ├── campaigns.py             ← CRUD + lancement campagnes
│   │   ├── ivr.py                   ← CRUD menus et options IVR
│   │   ├── config_router.py         ← Config agent, Ringover test
│   │   └── webhooks.py              ← Réception events Ringover
│   ├── services/
│   │   ├── ringover.py              ← Client API Ringover
│   │   ├── ai_service.py            ← Conversations GPT-4o
│   │   └── ivr_service.py           ← Moteur IVR
│   ├── templates/                   ← Pages HTML Jinja2
│   │   ├── base.html                ← Layout + sidebar + topbar
│   │   ├── dashboard.html           ← KPIs + graphiques
│   │   ├── calls.html               ← Liste appels + modale transcript
│   │   ├── leads.html               ← CRM leads
│   │   ├── campaigns.html           ← Liste campagnes
│   │   ├── campaign_builder.html    ← Wizard création (4 étapes)
│   │   ├── ivr_builder.html         ← Éditeur IVR
│   │   └── config.html              ← Config agent + Ringover
│   └── static/
│       ├── css/nexcall.css          ← Design system complet
│       └── js/nexcall.js            ← Utilitaires JS partagés
│
└── frontend/                        ← Composants standalone
    ├── components/
    │   ├── KPICards.html
    │   ├── CallModal.html
    │   └── Dialer.html
    ├── pages/
    │   └── standalone-dashboard.html
    └── campaign-builder/
        └── IVRBuilder.html
```

---

## Installation locale

```bash
# 1. Cloner ou dézipper le projet
cd nexcall

# 2. Environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Dépendances
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Éditez .env avec vos clés API

# 5. Lancement
uvicorn main:app --reload --port 8000
```

**Dashboard :** http://localhost:8000  
**API Docs :** http://localhost:8000/docs

---

## Configuration (.env)

```env
# Obligatoires pour production
RINGOVER_API_KEY=votre_cle_ringover
OPENAI_API_KEY=sk-votre_cle_openai

# Numéros téléphoniques
RINGOVER_PHONE_NUMBER=+33XXXXXXXXX
RINGOVER_TRANSFER_NUMBER=+33XXXXXXXXX

# Agent IA
AI_AGENT_NAME=Sophie
AI_COMPANY_NAME=AssurancePro
```

Sans ces clés, l'application démarre en **mode simulation** (données fictives).

---

## Déploiement sur Render

```bash
# 1. Pousser sur GitHub
git add .
git commit -m "NexCall AI v2.0"
git push origin main

# 2. Dans le Dashboard Render :
#    New → Web Service → GitHub repo
#    Render détecte render.yaml automatiquement

# 3. Configurer les variables d'environnement dans Render :
#    RINGOVER_API_KEY, OPENAI_API_KEY, etc.
```

> **Important :** `PYTHON_VERSION=3.11.9` est déjà dans `render.yaml` et `.python-version`.  
> Ne supprimez pas ces fichiers — ils forcent Python 3.11 au lieu de 3.14 (défaut Render).

---

## Webhooks Ringover

Dans **Ringover Console → Paramètres → API & Intégrations → Webhooks** :

| Événement | URL |
|-----------|-----|
| Tous événements | `https://votre-app.onrender.com/webhooks/ringover` |

**En développement local** avec ngrok :
```bash
ngrok http 8000
# Copiez l'URL https://xxxx.ngrok.io dans la console Ringover
# Mettez à jour BASE_URL dans .env
```

---

## Fonctionnalités

### Dashboard
- KPIs en temps réel (appels, leads, taux de succès, durée)
- Graphique volume d'appels (7/14/30 jours)
- Liste des appels récents avec statuts

### Appels
- Historique complet avec filtres (statut, direction)
- **Modale transcript** : conversation complète + résumé IA
- **Dialer intégré** : lancer un appel sortant depuis le dashboard
- Support appels entrants (IVR) et sortants (Agent IA)

### Leads
- Leads qualifiés automatiquement par l'IA (score 0-100)
- Filtre leads chauds (≥70) / froids
- Marquer comme contacté
- Export CSV

### Campagnes
- Wizard 4 étapes : Type → Offre → Contacts → Lancement
- Types : **Agent IA vocal** ou **IVR téléphonique**
- Offres prédéfinies : Auto, Santé, Mutuelle, Immobilier, Crédit
- Script vocal personnalisable
- Import liste de contacts (un numéro par ligne)
- Lancement, pause, reprise

### Éditeur IVR
- Création de menus DTMF visuels
- Actions par touche : Agent IA / Transfert / Message / Raccrocher
- Glisser-déposer pour réordonner les options
- Aperçu vocal en temps réel

### Configuration Agent IA
- Nom, entreprise, langue, voix OpenAI (nova, alloy, echo…)
- Prompt système personnalisable
- Test connexion Ringover
- URLs webhooks à copier

---

## API Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/calls/stats?days=7` | Statistiques KPIs |
| GET | `/api/calls/` | Liste des appels |
| GET | `/api/calls/{id}/detail` | Détail + transcript |
| POST | `/api/calls/outbound` | Lancer appel sortant |
| GET | `/api/leads/` | Liste des leads |
| GET | `/api/leads/export/csv` | Export CSV |
| PATCH | `/api/leads/{id}/contacted` | Marquer contacté |
| GET | `/api/campaigns/` | Liste des campagnes |
| POST | `/api/campaigns/` | Créer une campagne |
| POST | `/api/campaigns/{id}/launch` | Lancer la campagne |
| GET | `/api/ivr/menu/{campaign_id}` | Menu IVR |
| POST | `/api/ivr/option` | Ajouter option IVR |
| GET | `/api/config/agent` | Config agent IA |
| PUT | `/api/config/agent` | Sauvegarder config |
| GET | `/api/config/ringover/test` | Test connexion |
| POST | `/webhooks/ringover` | Webhook Ringover |
| GET | `/health` | Health check |

---

## Architecture du flux d'appel

```
Appel entrant Ringover
      ↓
POST /webhooks/ringover (event: RINGING)
      ↓
IVR: "Tapez 1 pour Auto, 2 pour Santé…"
      ↓
Appelant tape une touche (event: DTMF)
      ↓
Si touche 1/2/3 → Agent IA vocal
│     ↓
│  OpenAI GPT-4o comprend la conversation
│  Score lead calculé automatiquement
│  Si score ≥ 70 → Lead "chaud" créé
      ↓
Si touche 4 → Transfert agent humain
      ↓
Fin d'appel (event: HANGUP)
│  → Transcript sauvegardé
│  → Résumé IA généré
│  → Lead mis à jour en BDD
```

---

## Variables d'environnement complètes

| Variable | Valeur par défaut | Description |
|----------|------------------|-------------|
| `APP_NAME` | NexCall AI | Nom affiché |
| `APP_PORT` | 8000 | Port local |
| `DEBUG` | false | Mode debug |
| `DATABASE_URL` | sqlite+aiosqlite:///./data/nexcall.db | BDD |
| `RINGOVER_API_KEY` | — | **Requis en prod** |
| `RINGOVER_PHONE_NUMBER` | — | Numéro émetteur |
| `RINGOVER_TRANSFER_NUMBER` | — | Numéro agents humains |
| `OPENAI_API_KEY` | — | **Requis pour l'IA** |
| `OPENAI_MODEL` | gpt-4o | Modèle IA |
| `OPENAI_TTS_VOICE` | nova | Voix TTS |
| `AI_AGENT_NAME` | Sophie | Nom de l'agent |
| `AI_COMPANY_NAME` | AssurancePro | Nom entreprise |
| `LEAD_SCORE_THRESHOLD` | 70 | Score lead "chaud" |

---

## Support

- **API Docs** : `http://localhost:8000/docs`
- **Health check** : `http://localhost:8000/health`
- **Logs** : `./logs/` (créé automatiquement)
