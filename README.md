# 📚 VCE Vocabulary Flashcards

A comprehensive web application for Year 6-12 students to learn vocabulary through interactive flashcards with AI-powered search.

**Tech Stack**: FastAPI + Jinja2 + SQLite + Azure OpenAI

## ✨ Features

### 🎯 Study Sessions
- **Custom Study Modes**: Mixed Practice, New Words, Review Words, Difficult Words
- **Configurable Goals**: 5-30 words per session with optional time limits
- **Live Progress Tracking**: Circular progress indicators and real-time statistics
- **Session Controls**: Pause/Resume/Reset with achievement notifications

### 💯 Smart Learning
- **Difficulty Rating**: Rate words as Easy/Medium/Hard with visual indicators
- **Mastery Tracking**: Progress from New → Learning → Mastered with color-coded dots
- **Advanced Filtering**: Filter by difficulty, search content, word types
- **Keyboard Navigation**: Arrow keys, spacebar, and hotkeys for efficient study

### 🤖 AI Integration
- **Azure OpenAI Search**: Ask questions about vocabulary and get intelligent responses
- **Smart Word Selection**: Algorithm suggests words based on your learning progress
- **AI Learning Sessions**: Adaptive learning with session tracking

### 🎮 Enhanced Experience
- **Dark/Light Themes**: Toggle between themes with persistent preferences
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Visual Feedback**: Animations, progress rings, and achievement popups
- **Word Management**: Add, edit, remove, hide/show cards
- **Multi-User Support**: Individual accounts with profiles and progress tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Azure OpenAI API access (optional for AI search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/promisinganuj/kids-vocabulary-app.git
   cd kids-vocabulary-app
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

4. **Configure Azure OpenAI (Optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

5. **Start the application**
   ```bash
   chmod +x start_app.sh
   ./start_app.sh
   ```

6. **Open your browser** to `http://localhost:5001`
7. **API documentation** at `http://localhost:5001/docs`

## ⚙️ Configuration

### Azure OpenAI Setup
Create a `.env` file in the `app/` directory with:

```bash
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

Without Azure OpenAI, the app works fully except for the AI search feature.

## ☁️ Deploy to Azure

Host the app on **Azure Container Apps** with one command:

```bash
az login
./infra/deploy.sh
```

This creates an Azure Container Registry, Container Apps Environment, persistent storage for SQLite, and deploys the app with HTTPS. Auto-scales from 0–2 replicas (~$5-20/month for low traffic).

For CI/CD with GitHub Actions (auto-deploy on push to `main`), see [infra/README.md](infra/README.md).

## 📖 How to Use

### Starting a Study Session
1. Choose your **Study Mode** (Mixed/New/Review/Difficult)
2. Set your **Word Goal** (5-30 words)
3. Optionally set a **Time Limit** (5-30 minutes)
4. Click **"🚀 Start Custom Session"** or **"⚡ Quick Start"**

### Learning with Flashcards
- **Click cards** to flip and see definitions
- **Use ✓ Know / ✗ Review** buttons to track progress
- **Hover over cards** to rate difficulty (E/M/H buttons)
- **Press spacebar** to flip focused card
- **Use arrow keys** to navigate between cards

### Advanced Features
- **Dark Mode**: Click 🌙 button (top-right)
- **Search**: Use AI to ask questions about vocabulary
- **Filter**: Use difficulty dropdown to focus on specific levels
- **Hide/Show**: Use × button to hide cards temporarily

## 📁 Project Structure

```
kids-vocabulary-app/
├── app/
│   ├── data/
│   │   ├── vocabulary.db          # SQLite database (auto-created)
│   │   └── datamodel.md           # Database schema documentation
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── flashcards.html        # Main flashcard interface
│   │   ├── ai_learning.html       # AI-powered learning sessions
│   │   ├── manage.html            # Word management interface
│   │   ├── admin.html             # Admin dashboard
│   │   ├── profile.html           # User profile
│   │   ├── login.html             # Authentication
│   │   ├── register.html          # User registration
│   │   └── ...                    # Error pages, password reset
│   ├── fastapi_web_flashcards.py  # Main FastAPI application
│   ├── fastapi_auth.py            # Authentication module
│   ├── database_manager.py        # Database operations (SQLite)
│   ├── Dockerfile                 # Container build
│   ├── requirements.txt           # Python dependencies
│   ├── start_app.sh               # Application launcher
│   └── fastapi_start_app.sh       # FastAPI/Uvicorn startup
├── .github/workflows/            # CI/CD pipelines
│   └── deploy-azure.yml           # Azure Container Apps deployment
├── infra/                         # Azure Container App deployment
│   ├── main.bicep                 # Infrastructure-as-code (Bicep)
│   ├── main.parameters.json       # Deployment parameters
│   ├── deploy.sh                  # One-command deployment script
│   └── README.md                  # Deployment documentation
├── seed-data/
│   └── words-list.txt             # Initial vocabulary data
├── utils/                         # Admin utilities
│   ├── load-words-to-base-vocab.py
│   └── managing-vocab-as-admin/   # Vocabulary management scripts
└── README.md
```

## 🔧 Core Files

- `app/fastapi_web_flashcards.py` - Main FastAPI application with all routes
- `app/fastapi_auth.py` - Session-based authentication
- `app/database_manager.py` - SQLite database operations (multi-user)
- `app/templates/flashcards.html` - Main study interface
- `app/requirements.txt` - Python dependencies

## 📊 Database

The app uses SQLite with 12 tables supporting:
- **Users** — accounts, profiles, sessions, preferences
- **Vocabulary** — per-user word libraries with progress tracking
- **Base Vocabulary** — shared word bank (3,738 words) copied to new users
- **Study Sessions** — session tracking, AI learning sessions
- **Social** — word likes, community features

See `app/data/datamodel.md` for full schema documentation.

## 🎯 Study Tips

1. **Start with Mixed Practice** to get a balanced review
2. **Rate difficult words as "Hard"** so they appear more frequently
3. **Use "New Words" mode** when you want to learn fresh vocabulary
4. **Set achievable goals** (start with 10 words, increase gradually)
5. **Study regularly** — short daily sessions beat long weekly ones
6. **Use the AI search** for deeper understanding of difficult words

## 🆘 Troubleshooting

**App won't start:**
```bash
cd app
pip install -r requirements.txt
python fastapi_web_flashcards.py
```

**Database errors:**
```bash
cp data/vocabulary.db.backup data/vocabulary.db
```

**Azure OpenAI not working:**
- Check `.env` credentials
- Verify Azure OpenAI deployment is active

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Happy Learning! 📖✨**

Built with ❤️ for VCE students and vocabulary enthusiasts.
