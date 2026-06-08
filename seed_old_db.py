import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "letter_platform.db")

OLD_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) DEFAULT '' UNIQUE,
    email VARCHAR(200) DEFAULT '' UNIQUE,
    hashed_password VARCHAR(200) NOT NULL,
    display_name VARCHAR(100) DEFAULT '',
    avatar VARCHAR(500) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS family_spaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    cover_image VARCHAR(500) DEFAULT '',
    creator_id INTEGER NOT NULL REFERENCES users(id),
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_space_id INTEGER NOT NULL REFERENCES family_spaces(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role VARCHAR(50) DEFAULT 'visitor',
    nickname VARCHAR(100) DEFAULT '',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS family_invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_space_id INTEGER NOT NULL REFERENCES family_spaces(id),
    inviter_id INTEGER NOT NULL REFERENCES users(id),
    invitee_user_id INTEGER REFERENCES users(id),
    invitee_phone VARCHAR(20) DEFAULT '',
    invitee_email VARCHAR(200) DEFAULT '',
    code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',
    message TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);

CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_space_id INTEGER NOT NULL REFERENCES family_spaces(id),
    name VARCHAR(100) NOT NULL,
    alias VARCHAR(100) DEFAULT '',
    gender VARCHAR(10) DEFAULT '',
    birth_year VARCHAR(20) DEFAULT '',
    death_year VARCHAR(20) DEFAULT '',
    bio TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_space_id INTEGER NOT NULL REFERENCES family_spaces(id),
    title VARCHAR(300) NOT NULL,
    description TEXT DEFAULT '',
    sender_id INTEGER REFERENCES persons(id),
    receiver_id INTEGER REFERENCES persons(id),
    send_location VARCHAR(200) DEFAULT '',
    receive_location VARCHAR(200) DEFAULT '',
    send_date VARCHAR(50) DEFAULT '',
    receive_date VARCHAR(50) DEFAULT '',
    era VARCHAR(50) DEFAULT '',
    category VARCHAR(50) DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    visibility VARCHAR(20) DEFAULT 'family',
    is_starred BOOLEAN DEFAULT 0,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS letter_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_id INTEGER NOT NULL REFERENCES letters(id),
    page_number INTEGER NOT NULL,
    image_path VARCHAR(500) DEFAULT '',
    transcription TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_id INTEGER NOT NULL REFERENCES letters(id),
    file_name VARCHAR(300) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER DEFAULT 0,
    media_type VARCHAR(20) DEFAULT 'image',
    description TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS share_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_id INTEGER NOT NULL REFERENCES letters(id),
    creator_id INTEGER NOT NULL REFERENCES users(id),
    token VARCHAR(100) NOT NULL UNIQUE,
    access_level VARCHAR(20) DEFAULT 'view',
    max_views INTEGER DEFAULT 0,
    current_views INTEGER DEFAULT 0,
    is_active VARCHAR(10) DEFAULT 'yes',
    password VARCHAR(200) DEFAULT '',
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

SEED_DATA = """
INSERT INTO users (username, phone, email, hashed_password, display_name) VALUES
('old_owner', '11100000001', 'old_owner@test.com', '$2b$12$fakehash1', '旧馆主'),
('old_editor', '11100000002', 'old_editor@test.com', '$2b$12$fakehash2', '旧整理员'),
('old_visitor', '11100000003', 'old_visitor@test.com', '$2b$12$fakehash3', '旧访客');

INSERT INTO family_spaces (name, description, creator_id, is_public) VALUES
('旧家庭馆', '升级前创建的馆', 1, 0);

INSERT INTO family_members (family_space_id, user_id, role, nickname) VALUES
(1, 1, 'owner', '馆主'),
(1, 2, 'editor', '整理员'),
(1, 3, 'visitor', '访客');

INSERT INTO family_invitations (family_space_id, inviter_id, invitee_phone, code, status, expires_at) VALUES
(1, 1, '11100000099', 'old_code_abc123', 'pending', '2099-12-31 23:59:59');

INSERT INTO persons (family_space_id, name, alias, gender) VALUES
(1, '张三', '三叔', 'male'),
(1, '李四', '四婶', 'female');

INSERT INTO letters (family_space_id, title, description, sender_id, receiver_id, era, category, tags, visibility, created_by) VALUES
(1, '旧信件一', '升级前创建的信件', 1, 2, '民国', '家书', '亲情', 'family', 1),
(1, '旧信件二', '另一封旧信', 2, 1, '民国', '家书', '思念', 'private', 2);

INSERT INTO letter_pages (letter_id, page_number, transcription) VALUES
(1, 1, '旧释文第一页内容'),
(1, 2, '旧释文第二页内容'),
(2, 1, '第二封信释文');

INSERT INTO share_links (letter_id, creator_id, token, access_level, max_views, is_active) VALUES
(1, 1, 'old_share_token_xyz', 'view', 10, 'yes');
"""


def seed_old_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(OLD_SCHEMA)
    conn.executescript(SEED_DATA)
    conn.commit()
    conn.close()
    print(f"旧库已创建: {DB_PATH}")
    print("包含: 3用户, 1家庭馆, 3成员, 1邀请, 2人物, 2信件, 3释文页, 1分享链接")


if __name__ == "__main__":
    seed_old_db()
