# Vocabulary App Database Documentation

## Overview
This document describes the database schema for the Kids Vocabulary Flashcard Application. The application uses PostgreSQL as its database engine and supports multi-user functionality with comprehensive vocabulary management, study tracking, and AI-powered learning features.

**Database**: PostgreSQL  
**Engine**: PostgreSQL  
**Current Tables**: 12 tables (cleaned up on Sep 16, 2025)  
**Database Size**: Active with 3 users, 11,245 user vocabulary words, 3,738 base vocabulary words

---

## Table Structure & Relationships

### 1. **users** (Core User Management) 🔑
**Purpose**: Stores user account information and profiles for the multi-user vocabulary application.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique user identifier |
| `email` | TEXT | NOT NULL UNIQUE COLLATE NOCASE | User's email address (case-insensitive) |
| `username` | TEXT | NOT NULL UNIQUE COLLATE NOCASE | User's display name (case-insensitive) |
| `password_hash` | TEXT | NOT NULL | Hashed password using hashlib |
| `salt` | TEXT | NOT NULL | Password salt for security |
| `is_active` | BOOLEAN | DEFAULT 1 | Account status (active/inactive) |
| `is_admin` | BOOLEAN | DEFAULT 0 | Administrative privileges flag |
| `email_verified` | BOOLEAN | DEFAULT 0 | Email verification status |
| `verification_token` | TEXT | | Email verification token |
| `reset_token` | TEXT | | Password reset token (deprecated - see password_reset_tokens) |
| `reset_token_expires` | TIMESTAMP | | Reset token expiration (deprecated) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last profile update |
| `last_login` | TIMESTAMP | | Last successful login |
| `login_count` | INTEGER | DEFAULT 0 | Total number of logins |
| `first_name` | TEXT | | User's first name |
| `last_name` | TEXT | | User's last name |
| `mobile_number` | TEXT | | Contact phone number |
| `profile_type` | TEXT | DEFAULT "Student" | User role (Student, Teacher, etc.) |
| `class_year` | INTEGER | | Academic class/grade level |
| `date_of_birth` | DATE | | Birth date (deprecated - see year_of_birth) |
| `year_of_birth` | INTEGER | | Birth year for age-appropriate content |
| `school_name` | TEXT | | Educational institution |
| `preferred_study_time` | TEXT | | Preferred learning schedule |
| `learning_goals` | TEXT | | Personal learning objectives |
| `avatar_color` | TEXT | DEFAULT "#3498db" | Profile color theme |

**Indexes**: `idx_users_email`, `idx_users_username`  
**Triggers**: `update_user_timestamp` (auto-updates `updated_at`)  
**Status**: ✅ **ACTIVELY USED** (3 users registered)

---

### 2. **user_sessions** (Authentication Management) 🔐
**Purpose**: Manages user login sessions and security tokens for web authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Session record ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User owning this session |
| `session_token` | TEXT | NOT NULL UNIQUE | Unique session identifier |
| `expires_at` | TIMESTAMP | NOT NULL | Session expiration time |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Session creation time |
| `last_accessed` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last activity timestamp |
| `ip_address` | TEXT | | Client IP address |
| `user_agent` | TEXT | | Browser/client information |

**Indexes**: `idx_sessions_token`, `idx_sessions_user`  
**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (Session management)

---

### 3. **vocabulary** (User Vocabulary Library) 📚
**Purpose**: Stores individual user's vocabulary words with learning progress tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Vocabulary entry ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | Owner of this vocabulary word |
| `word` | TEXT | NOT NULL COLLATE NOCASE | The vocabulary word (case-insensitive) |
| `word_type` | TEXT | NOT NULL | Part of speech (Noun, Verb, Adjective, etc.) |
| `definition` | TEXT | NOT NULL | Word definition/meaning |
| `example` | TEXT | NOT NULL | Example sentence using the word |
| `difficulty` | TEXT | DEFAULT 'medium' | Difficulty level (easy/medium/hard) |
| `times_reviewed` | INTEGER | DEFAULT 0 | Number of times studied |
| `times_correct` | INTEGER | DEFAULT 0 | Number of correct answers |
| `last_reviewed` | TIMESTAMP | | Last study session timestamp |
| `mastery_level` | INTEGER | DEFAULT 0 | Learning progress indicator |
| `is_favorite` | BOOLEAN | DEFAULT 0 | User marked as favorite |
| `tags` | TEXT | DEFAULT '' | Custom user tags |
| `source` | TEXT | DEFAULT 'manual' | How word was added (manual/import/ai) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When word was added |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification time |
| `base_word_id` | INTEGER | FK → base_vocabulary(id) | Reference to base vocabulary |
| `like_count` | INTEGER | DEFAULT 0 | Number of likes from other users |
| `is_hidden` | INTEGER | DEFAULT 0 | Hidden from user's active vocabulary |

**Unique Constraint**: `(user_id, word)` - One word per user  
**Indexes**: `idx_vocab_user`, `idx_vocab_word`, `idx_vocab_difficulty`, `idx_vocab_base_word`  
**Triggers**: `update_vocabulary_timestamp` (auto-updates `updated_at`)  
**Relationships**: References `users` and `base_vocabulary` tables  
**Status**: ✅ **HEAVILY USED** (11,245 user vocabulary entries)

---

### 4. **base_vocabulary** (Master Word Repository) 🌟
**Purpose**: Central repository of approved vocabulary words that can be shared across all users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Base vocabulary ID |
| `word` | TEXT | NOT NULL UNIQUE COLLATE NOCASE | The vocabulary word (case-insensitive) |
| `word_type` | TEXT | NOT NULL | Part of speech |
| `definition` | TEXT | NOT NULL | Standard definition |
| `example` | TEXT | NOT NULL | Example sentence |
| `difficulty` | TEXT | DEFAULT 'medium' | Recommended difficulty level |
| `category` | TEXT | DEFAULT 'general' | Word category/subject |
| `total_likes` | INTEGER | DEFAULT 0 | Total likes across all users |
| `is_active` | BOOLEAN | DEFAULT 1 | Active/inactive status |
| `created_by` | INTEGER | FK → users(id) SET NULL | User who created this entry |
| `approved_by` | INTEGER | FK → users(id) SET NULL | Admin who approved this entry |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| `created_by_user_id` | INTEGER | DEFAULT 1 | Legacy creator reference |

**Indexes**: `idx_base_vocab_word`  
**Relationships**: References `users` table for creators and approvers  
**Status**: ✅ **ACTIVELY USED** (3,738 base vocabulary words)

---

### 5. **word_likes** (User Engagement Tracking) ❤️
**Purpose**: Tracks which users have liked specific vocabulary words for popularity metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Like record ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User who liked the word |
| `word_id` | INTEGER | NOT NULL, FK → vocabulary(id) CASCADE | Vocabulary word that was liked |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the like was given |

**Unique Constraint**: `(user_id, word_id)` - One like per user per word  
**Indexes**: `idx_word_likes_user`, `idx_word_likes_word`  
**Relationships**: References `users` and `vocabulary` tables  
**Status**: ✅ **ACTIVELY USED** (User engagement feature)

---

### 6. **password_reset_tokens** (Security Management) 🔑
**Purpose**: Manages secure password reset tokens with expiration tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Token record ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User requesting password reset |
| `token` | TEXT | NOT NULL UNIQUE | Secure reset token |
| `expires_at` | TIMESTAMP | NOT NULL | Token expiration time |
| `used` | BOOLEAN | DEFAULT 0 | Whether token has been used |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Token creation time |

**Indexes**: `idx_reset_tokens_token`, `idx_reset_tokens_user`  
**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (Password reset functionality)

---

### 7. **study_sessions** (Learning Session Tracking) 📖
**Purpose**: Records user study sessions with performance metrics and goals.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Study session ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User conducting the session |
| `session_type` | TEXT | DEFAULT 'review' | Type of study session |
| `start_time` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Session start time |
| `end_time` | TIMESTAMP | | Session completion time |
| `words_reviewed` | INTEGER | DEFAULT 0 | Number of words studied |
| `words_correct` | INTEGER | DEFAULT 0 | Number of correct answers |
| `duration_seconds` | INTEGER | DEFAULT 0 | Total session duration |
| `session_goal` | INTEGER | DEFAULT 10 | Target number of words |
| `accuracy_percentage` | REAL | DEFAULT 0 | Session accuracy rate |
| `is_completed` | BOOLEAN | DEFAULT 0 | Whether session was finished |
| `notes` | TEXT | DEFAULT '' | User notes about the session |

**Indexes**: `idx_study_sessions_user`  
**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (14 study sessions recorded)

---

### 8. **study_session_words** (Detailed Word Performance) 📊
**Purpose**: Tracks individual word performance within study sessions for detailed analytics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Record ID |
| `session_id` | INTEGER | NOT NULL, FK → study_sessions(id) CASCADE | Parent study session |
| `word_id` | INTEGER | NOT NULL, FK → vocabulary(id) CASCADE | Vocabulary word studied |
| `was_correct` | BOOLEAN | NOT NULL | Whether answer was correct |
| `response_time_ms` | INTEGER | DEFAULT 0 | Response time in milliseconds |
| `attempts` | INTEGER | DEFAULT 1 | Number of attempts for this word |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When word was studied |

**Relationships**: References `study_sessions` and `vocabulary` tables  
**Status**: ✅ **ACTIVELY USED** (Detailed performance tracking)

---

### 9. **user_preferences** (User Settings) ⚙️
**Purpose**: Stores user-specific application settings and preferences.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Preference record ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User owning the preference |
| `preference_key` | TEXT | NOT NULL | Setting name/identifier |
| `preference_value` | TEXT | NOT NULL | Setting value |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When preference was set |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification time |

**Unique Constraint**: `(user_id, preference_key)` - One value per setting per user  
**Indexes**: `idx_preferences_user`  
**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (User customization)

---

### 10. **ai_suggestion_feedback** (AI Learning Analytics) 🤖
**Purpose**: Tracks user feedback on AI-suggested vocabulary words for machine learning improvement.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Feedback record ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) | User providing feedback |
| `suggested_word` | TEXT | NOT NULL | AI-suggested vocabulary word |
| `difficulty_rating` | TEXT | NOT NULL | User's difficulty assessment |
| `added_to_vocabulary` | BOOLEAN | NOT NULL | Whether user added the word |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Feedback timestamp |

**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (AI improvement system)

---

### 11. **ai_learning_sessions** (AI-Powered Study Sessions) 🧠
**Purpose**: Manages AI-driven adaptive learning sessions with intelligent word selection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | AI session ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) CASCADE | User taking the session |
| `target_words` | INTEGER | NOT NULL DEFAULT 10 | Target number of words |
| `words_completed` | INTEGER | DEFAULT 0 | Words completed so far |
| `words_correct` | INTEGER | DEFAULT 0 | Correct answers count |
| `current_difficulty` | TEXT | DEFAULT 'medium' | Current difficulty level |
| `session_started_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Session start time |
| `session_ended_at` | TIMESTAMP | | Session completion time |
| `is_completed` | BOOLEAN | DEFAULT 0 | Session completion status |
| `total_time_seconds` | INTEGER | DEFAULT 0 | Total session duration |

**Indexes**: `idx_ai_sessions_user`  
**Relationships**: References `users` table  
**Status**: ✅ **ACTIVELY USED** (4 AI learning sessions)

---

### 12. **ai_learning_session_words** (AI Session Word Details) 🎯
**Purpose**: Tracks individual word interactions within AI-powered learning sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Session word record ID |
| `session_id` | INTEGER | NOT NULL, FK → ai_learning_sessions(id) CASCADE | Parent AI session |
| `word_id` | INTEGER | FK → vocabulary(id) SET NULL | User's vocabulary word (if exists) |
| `base_word_id` | INTEGER | FK → base_vocabulary(id) SET NULL | Base vocabulary reference |
| `word_text` | TEXT | NOT NULL | The actual word text |
| `user_response` | TEXT | | User's answer/response |
| `is_correct` | BOOLEAN | | Whether response was correct |
| `response_time_ms` | INTEGER | DEFAULT 0 | Response time in milliseconds |
| `difficulty_level` | TEXT | DEFAULT 'medium' | Word difficulty level |
| `word_order` | INTEGER | DEFAULT 0 | Order within the session |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When word was presented |

**Indexes**: `idx_ai_session_words_session`  
**Relationships**: References `ai_learning_sessions`, `vocabulary`, and `base_vocabulary` tables  
**Status**: ✅ **ACTIVELY USED** (AI session tracking)

---

## Database Relationships Overview

### Primary Relationships
1. **users** → **vocabulary** (1:N) - Each user owns multiple vocabulary words
2. **users** → **study_sessions** (1:N) - Each user has multiple study sessions
3. **users** → **user_preferences** (1:N) - Each user has multiple settings
4. **users** → **vocabulary_lists** (1:N) - Each user can create multiple lists
5. **base_vocabulary** → **vocabulary** (1:N) - Base words can be used by multiple users

### Junction Tables
- **vocabulary_list_words** - Links vocabulary words to custom lists (M:N)
- **word_likes** - Links users to vocabulary words they've liked (M:N)
- **study_session_words** - Links study sessions to specific words studied
- **ai_learning_session_words** - Links AI sessions to words presented

### Authentication & Security
- **user_sessions** - Active login sessions
- **password_reset_tokens** - Secure password reset workflow

### Analytics & Tracking
- **ai_suggestion_feedback** - AI system improvement data

---

## Index Strategy

The database includes strategic indexes to optimize common query patterns:

- **User lookups**: `idx_users_email`, `idx_users_username`
- **Vocabulary queries**: `idx_vocab_user`, `idx_vocab_word`, `idx_vocab_difficulty`
- **Session management**: `idx_sessions_token`, `idx_sessions_user`
- **AI features**: `idx_ai_sessions_user`, `idx_ai_session_words_session`

---

## Database Triggers

The database uses triggers for automatic data maintenance:

1. **update_vocabulary_timestamp** - Auto-updates vocabulary `updated_at` field
2. **update_user_timestamp** - Auto-updates user `updated_at` field

---

## Usage Status Summary

| Status | Tables | Description |
|--------|--------|-------------|
| ✅ **HEAVILY USED** | `vocabulary`, `base_vocabulary` | Core vocabulary storage (15,000+ records) |
| ✅ **ACTIVELY USED** | `users`, `study_sessions`, `ai_learning_sessions` | User management and sessions |
| ✅ **ACTIVELY USED** | `user_preferences`, `ai_suggestion_feedback` | User customization and AI feedback |
| ✅ **ACTIVELY USED** | `word_likes`, `password_reset_tokens`, `user_sessions` | Engagement and security |
| 📊 **JUNCTION TABLES** | `study_session_words`, `ai_learning_session_words` | Active relationship management |

---

## Data Integrity & Constraints

- **Foreign Key Constraints**: All relationships use proper foreign key constraints with CASCADE or SET NULL behaviors
- **Unique Constraints**: Prevent duplicate users, sessions, and list memberships
- **Default Values**: Sensible defaults for timestamps, counters, and flags
- **Case-Insensitive Text**: User emails, usernames, and vocabulary words use COLLATE NOCASE
- **Boolean Flags**: Consistent use of 0/1 for boolean values

---

*Last Updated: September 16, 2025*  
*Database Version: Multi-user Vocabulary App v2.0 (Legacy cleanup completed)*

## ✅ Database Cleanup Completed (Sep 16, 2025)

Successfully removed **4 legacy tables** that were not being used:
- ❌ `vocabulary_lists` - Custom word collections (removed)
- ❌ `vocabulary_list_words` - List-word associations (removed)  
- ❌ `user_achievements` - Gamification system (removed)
- ❌ `daily_stats` - Daily analytics tracking (removed)

**Also cleaned up:**
- ❌ Triggers: `update_list_word_count`, `update_list_word_count_delete`
- ❌ Index: `idx_daily_stats_user_date`

**Database is now optimized** with only actively used tables and components. The application runs perfectly after cleanup! 🎉