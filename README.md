# 📚 VCE Vocabulary Flashcards

A comprehensive web application for Year 6-12 students to learn vocabulary through interactive flashcards with AI-powered search.

## ✨ Features

### 🎯 **Study Sessions**
- **Custom Study Modes**: Mixed Practice, New Words, Review Words, Difficult Words
- **Configurable Goals**: 5-30 words per session with optional time limits
- **Live Progress Tracking**: Circular progress indicators and real-time statistics
- **Session Controls**: Pause/Resume/Reset with achievement notifications

### 💯 **Smart Learning**
- **Difficulty Rating**: Rate words as Easy/Medium/Hard with visual indicators
- **Mastery Tracking**: Progress from New → Learning → Mastered with color-coded dots
- **Advanced Filtering**: Filter by difficulty, search content, word types
- **Keyboard Navigation**: Arrow keys, spacebar, and hotkeys for efficient study

### 🤖 **AI Integration**
- **Azure OpenAI Search**: Ask questions about vocabulary and get intelligent responses
- **Smart Word Selection**: Algorithm suggests words based on your learning progress
- **Contextual Help**: Get explanations, examples, and usage tips

### 🎮 **Enhanced Experience**
- **Dark/Light Themes**: Toggle between themes with persistent preferences
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Visual Feedback**: Animations, progress rings, and achievement popups
- **Word Management**: Add, edit, remove, hide/show cards

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

## ⚙️ Configuration

### Azure OpenAI Setup
Create a `.env` file in the `app/` directory with:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
```

Without Azure OpenAI, the app works fully except for the AI search feature.

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
- **Keyboard Navigation**: Click a card then use arrow keys

## 📁 Project Structure

```
kids-vocabulary-app/
├── app/
│   ├── data/
│   │   └── vocabulary.db          # SQLite database
│   ├── templates/
│   │   ├── flashcards.html        # Main flashcard interface
│   │   └── manage.html            # Word management interface
│   ├── web_flashcards.py          # Main Flask application
│   ├── database_manager.py        # Database operations
│   ├── requirements.txt           # Python dependencies
│   ├── start_app.sh              # Application launcher
│   ├── .env.example              # Environment configuration template
│   └── config.json               # App configuration
├── seed-data/
│   └── words-list.txt            # Initial vocabulary data
└── README.md                     # This file
```

## 🔧 Core Files

### Essential Files (Never Delete)
- `app/web_flashcards.py` - Main Flask application
- `app/database_manager.py` - Database operations
- `app/templates/flashcards.html` - Main interface
- `app/templates/manage.html` - Word management
- `app/data/vocabulary.db` - Your vocabulary database
- `app/requirements.txt` - Python dependencies
- `app/start_app.sh` - Application launcher

### Configuration Files
- `app/.env` - Your Azure OpenAI credentials (create from .env.example)
- `app/config.json` - Application settings
- `seed-data/words-list.txt` - Initial vocabulary words

## 🎯 Study Tips

### Effective Learning Workflow
1. **Start with Mixed Practice** to get a balanced review
2. **Rate difficult words as "Hard"** so they appear more frequently
3. **Use "New Words" mode** when you want to learn fresh vocabulary
4. **Switch to "Difficult Words"** mode for focused practice
5. **Set achievable goals** (start with 10 words, increase gradually)
6. **Use keyboard navigation** for faster studying

### Maximizing Progress
- **Study regularly** - Short daily sessions are better than long weekly ones
- **Be honest with ratings** - Mark words as "Hard" if you're not confident
- **Use the AI search** to get deeper understanding of difficult words
- **Track your accuracy** - Aim for 80%+ before moving to new words

## 🆘 Troubleshooting

### Common Issues

**App won't start:**
```bash
# Make sure you're in the app directory
cd app
# Check if all dependencies are installed
pip install -r requirements.txt
# Try running directly
python web_flashcards.py
```

**Database errors:**
```bash
# Restore from backup (if available)
cp data/vocabulary.db.backup data/vocabulary.db
# Or reinitialize database
python database_manager.py
```

**Azure OpenAI search not working:**
- Check your `.env` file has correct credentials
- Verify your Azure OpenAI deployment is active
- Test without quotes in environment variables

### Getting Help
- Check the app logs in `app.log`
- Ensure all files in "Essential Files" section are present
- Verify Python version is 3.8 or higher

## 📊 Database Schema

The app uses SQLite with this structure:
- **Words**: id, word, word_type, definition, example
- **Progress**: difficulty, mastery_level, times_reviewed, last_reviewed
- **Sessions**: study session tracking and analytics

## 🔮 Advanced Usage

### Adding New Words
1. Go to `/manage` URL in your browser
2. Use the "Add New Word" form
3. Or directly edit `seed-data/words-list.txt` and restart the app

### Backup Your Data
```bash
# Backup your vocabulary database
cp app/data/vocabulary.db app/data/vocabulary.db.backup
```

### Custom Vocabulary Lists
Edit `seed-data/words-list.txt` with your own words in this format:
```
word|word_type|definition|example
```

## 🏆 Achievement System

Unlock achievements as you study:
- **📚 First Steps**: Complete your first study session
- **🔥 Streak Master**: Study for 7 consecutive days
- **🎯 Perfect Score**: Achieve 100% accuracy in a session
- **💪 Challenge Completed**: Master 10+ difficult words

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a personal vocabulary learning tool. Feel free to fork and customize for your own use!

---

**Happy Learning! 📖✨**

Built with ❤️ for VCE students and vocabulary enthusiasts.
