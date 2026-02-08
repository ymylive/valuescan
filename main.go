package main

import (
	"nofx/logger"

	"github.com/joho/godotenv"
)

func main() {
	_ = godotenv.Load()
	logger.Init(nil)
	logger.Info("已移除 AI 交易与自动交易组件，Go 服务不再启动交易模块。")
}
