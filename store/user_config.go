package store

import (
	"database/sql"
	"fmt"
)

// UserConfigStore 用户配置存储
type UserConfigStore struct {
	db *sql.DB
}

// NewUserConfigStore 创建用户配置存储
func NewUserConfigStore(db *sql.DB) *UserConfigStore {
	return &UserConfigStore{db: db}
}

// InitSchema 初始化表结构
func (s *UserConfigStore) InitSchema() error {
	query := `
	CREATE TABLE IF NOT EXISTS user_configs (
		user_id TEXT NOT NULL,
		config_key TEXT NOT NULL,
		config_value TEXT NOT NULL,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (user_id, config_key)
	)`

	_, err := s.db.Exec(query)
	return err
}

// Get 获取用户配置
func (s *UserConfigStore) Get(userID, key string) (string, error) {
	var value string
	err := s.db.QueryRow(
		"SELECT config_value FROM user_configs WHERE user_id = ? AND config_key = ?",
		userID, key,
	).Scan(&value)

	if err == sql.ErrNoRows {
		return "", fmt.Errorf("config not found")
	}

	return value, err
}

// Set 设置用户配置
func (s *UserConfigStore) Set(userID, key, value string) error {
	_, err := s.db.Exec(`
		INSERT INTO user_configs (user_id, config_key, config_value, updated_at)
		VALUES (?, ?, ?, CURRENT_TIMESTAMP)
		ON CONFLICT(user_id, config_key) DO UPDATE SET
			config_value = excluded.config_value,
			updated_at = CURRENT_TIMESTAMP
	`, userID, key, value)

	return err
}

// Delete 删除用户配置
func (s *UserConfigStore) Delete(userID, key string) error {
	_, err := s.db.Exec(
		"DELETE FROM user_configs WHERE user_id = ? AND config_key = ?",
		userID, key,
	)
	return err
}

// GetAll 获取用户所有配置
func (s *UserConfigStore) GetAll(userID string) (map[string]string, error) {
	rows, err := s.db.Query(
		"SELECT config_key, config_value FROM user_configs WHERE user_id = ?",
		userID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	configs := make(map[string]string)
	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			return nil, err
		}
		configs[key] = value
	}

	return configs, rows.Err()
}
