-- ============================================
-- ФАЙЛЫ (универсальные)
-- ============================================

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    telegram_file_id TEXT NOT NULL,
    file_name TEXT,
    mime_type TEXT,
    file_size INTEGER,
    file_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ОСНОВНЫЕ СУЩНОСТИ
-- ============================================

CREATE TABLE communities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    avatar_file_id TEXT,
    logo_file_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(avatar_file_id) REFERENCES files(id),
    FOREIGN KEY(logo_file_id) REFERENCES files(id)
);

CREATE TABLE chats (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    chat_type TEXT NOT NULL,
    title TEXT,
    username TEXT,
    is_active INTEGER DEFAULT 1,
    settings TEXT DEFAULT '{}',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id),
    UNIQUE(community_id, chat_id)
);

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    is_bot INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    left_at TIMESTAMP,
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    UNIQUE(chat_id, user_id)
);

-- ============================================
-- РОЛИ И ПРАВА
-- ============================================

CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permissions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_permissions (
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    FOREIGN KEY(role_id) REFERENCES roles(id),
    FOREIGN KEY(permission_id) REFERENCES permissions(id),
    PRIMARY KEY(role_id, permission_id)
);

CREATE TABLE member_roles (
    chat_member_id INTEGER NOT NULL,
    role_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER,
    FOREIGN KEY(chat_member_id) REFERENCES chat_members(id),
    FOREIGN KEY(role_id) REFERENCES roles(id),
    PRIMARY KEY(chat_member_id, role_id)
);

-- ============================================
-- НАКАЗАНИЯ
-- ============================================

CREATE TABLE punishment_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE punishments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_member_id INTEGER NOT NULL,
    punishment_type_id TEXT NOT NULL,
    reason TEXT,
    duration INTEGER,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    issued_by INTEGER,
    is_active INTEGER DEFAULT 1,
    revoked_at TIMESTAMP,
    revoked_by INTEGER,
    revoked_reason TEXT,
    FOREIGN KEY(chat_member_id) REFERENCES chat_members(id),
    FOREIGN KEY(punishment_type_id) REFERENCES punishment_types(id)
);

-- ============================================
-- КОНТЕНТ (универсальный)
-- ============================================

CREATE TABLE content_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE content (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    content_type_id TEXT NOT NULL,
    file_id TEXT,
    url TEXT,
    text_content TEXT,
    order_num INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    views INTEGER DEFAULT 0,
    downloads INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY(content_type_id) REFERENCES content_types(id),
    FOREIGN KEY(file_id) REFERENCES files(id)
);

CREATE TABLE content_tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE content_tag_relations (
    content_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    FOREIGN KEY(content_id) REFERENCES content(id),
    FOREIGN KEY(tag_id) REFERENCES content_tags(id),
    PRIMARY KEY(content_id, tag_id)
);

-- ============================================
-- МЕНЮ И КНОПКИ
-- ============================================

CREATE TABLE menus (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_main INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    order_num INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id)
);

CREATE TABLE button_actions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE buttons (
    id TEXT PRIMARY KEY,
    menu_id TEXT NOT NULL,
    parent_button_id TEXT,
    text TEXT NOT NULL,
    action_type_id TEXT NOT NULL,
    action_data TEXT DEFAULT '{}',
    order_num INTEGER DEFAULT 0,
    row_num INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(menu_id) REFERENCES menus(id),
    FOREIGN KEY(parent_button_id) REFERENCES buttons(id),
    FOREIGN KEY(action_type_id) REFERENCES button_actions(id)
);

-- ============================================
-- ШАБЛОНЫ СООБЩЕНИЙ
-- ============================================

CREATE TABLE message_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message_variables (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message_templates (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL,
    message_type_id TEXT NOT NULL,
    chat_id TEXT,
    text TEXT,
    photo_file_id TEXT,
    document_file_id TEXT,
    buttons TEXT DEFAULT '[]',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id),
    FOREIGN KEY(message_type_id) REFERENCES message_types(id),
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(photo_file_id) REFERENCES files(id),
    FOREIGN KEY(document_file_id) REFERENCES files(id)
);

-- ============================================
-- ТРИГГЕРЫ
-- ============================================

CREATE TABLE triggers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    community_id TEXT NOT NULL,
    chat_id TEXT,
    reply_type TEXT NOT NULL,
    content_id TEXT,
    message_template_id TEXT,
    is_forward INTEGER DEFAULT 0,
    forward_chat_id TEXT,
    forward_message_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id),
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(content_id) REFERENCES content(id),
    FOREIGN KEY(message_template_id) REFERENCES message_templates(id)
);

CREATE TABLE trigger_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    is_case_sensitive INTEGER DEFAULT 0,
    is_regex INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trigger_id) REFERENCES triggers(id),
    UNIQUE(trigger_id, keyword)
);

-- ============================================
-- ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЕЙ (универсальные)
-- ============================================

CREATE TABLE user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(chat_id) REFERENCES chats(id)
);

-- ============================================
-- СТАТИСТИКА
-- ============================================

CREATE TABLE stat_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stats_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    user_id INTEGER,
    stat_type_id TEXT NOT NULL,
    date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(stat_type_id) REFERENCES stat_types(id),
    UNIQUE(chat_id, user_id, stat_type_id, date)
);

-- ============================================
-- СКАЧИВАНИЯ
-- ============================================

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    chat_id TEXT NOT NULL,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(content_id) REFERENCES content(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(chat_id) REFERENCES chats(id)
);

-- ============================================
-- ЛОГИ
-- ============================================

CREATE TABLE log_levels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_level_id TEXT NOT NULL,
    action TEXT NOT NULL,
    chat_id TEXT,
    user_id INTEGER,
    target_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(log_level_id) REFERENCES log_levels(id),
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- ============================================
-- НАСТРОЙКИ
-- ============================================

CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    community_id TEXT NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    value_type TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id),
    UNIQUE(community_id, category, key)
);

-- ============================================
-- ЗАДАЧИ
-- ============================================

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    data TEXT DEFAULT '{}',
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id)
);

-- ============================================
-- РАНГИ
-- ============================================

CREATE TABLE ranks (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT,
    icon TEXT,
    min_messages INTEGER DEFAULT 0,
    order_num INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(community_id) REFERENCES communities(id)
);

CREATE TABLE member_ranks (
    chat_member_id INTEGER NOT NULL,
    rank_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chat_member_id) REFERENCES chat_members(id),
    FOREIGN KEY(rank_id) REFERENCES ranks(id),
    PRIMARY KEY(chat_member_id, rank_id)
);

-- ============================================
-- ИНДЕКСЫ
-- ============================================

CREATE INDEX idx_chats_community ON chats(community_id);
CREATE INDEX idx_chat_members_chat ON chat_members(chat_id);
CREATE INDEX idx_chat_members_user ON chat_members(user_id);
CREATE INDEX idx_chat_members_last_seen ON chat_members(last_seen);
CREATE INDEX idx_chat_members_last_message ON chat_members(last_message_at);
CREATE INDEX idx_punishments_member ON punishments(chat_member_id);
CREATE INDEX idx_punishments_active ON punishments(is_active);
CREATE INDEX idx_punishments_expires ON punishments(expires_at);
CREATE INDEX idx_content_type ON content(content_type_id);
CREATE INDEX idx_content_active ON content(is_active);
CREATE INDEX idx_content_order ON content(order_num);
CREATE INDEX idx_buttons_menu ON buttons(menu_id);
CREATE INDEX idx_trigger_keywords_keyword ON trigger_keywords(keyword);
CREATE INDEX idx_stats_date ON stats_daily(date);
CREATE INDEX idx_logs_created ON logs(created_at);
CREATE INDEX idx_logs_action ON logs(action);
CREATE INDEX idx_member_ranks_member ON member_ranks(chat_member_id);
CREATE INDEX idx_tasks_scheduled ON tasks(scheduled_at);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_community ON tasks(community_id);
CREATE INDEX idx_settings_category ON settings(category);
CREATE INDEX idx_files_type ON files(file_type);
CREATE INDEX idx_user_actions_user ON user_actions(user_id);
CREATE INDEX idx_user_actions_chat ON user_actions(chat_id);
CREATE INDEX idx_user_actions_type ON user_actions(action_type);
CREATE INDEX idx_downloads_content ON downloads(content_id);
CREATE INDEX idx_downloads_user ON downloads(user_id);