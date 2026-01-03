package logger

import (
	"fmt"
	"log"
	"os"
)

var (
	infoLogger  *log.Logger
	warnLogger  *log.Logger
	errorLogger *log.Logger
)

// Init initializes the logger
func Init(config interface{}) {
	infoLogger = log.New(os.Stdout, "INFO: ", log.Ldate|log.Ltime|log.Lshortfile)
	warnLogger = log.New(os.Stdout, "WARN: ", log.Ldate|log.Ltime|log.Lshortfile)
	errorLogger = log.New(os.Stderr, "ERROR: ", log.Ldate|log.Ltime|log.Lshortfile)
}

// Info logs info message
func Info(v ...interface{}) {
	if infoLogger == nil {
		Init(nil)
	}
	infoLogger.Output(2, fmt.Sprint(v...))
}

// Infof logs formatted info message
func Infof(format string, v ...interface{}) {
	if infoLogger == nil {
		Init(nil)
	}
	infoLogger.Output(2, fmt.Sprintf(format, v...))
}

// Warn logs warning message
func Warn(v ...interface{}) {
	if warnLogger == nil {
		Init(nil)
	}
	warnLogger.Output(2, fmt.Sprint(v...))
}

// Warnf logs formatted warning message
func Warnf(format string, v ...interface{}) {
	if warnLogger == nil {
		Init(nil)
	}
	warnLogger.Output(2, fmt.Sprintf(format, v...))
}

// Error logs error message
func Error(v ...interface{}) {
	if errorLogger == nil {
		Init(nil)
	}
	errorLogger.Output(2, fmt.Sprint(v...))
}

// Errorf logs formatted error message
func Errorf(format string, v ...interface{}) {
	if errorLogger == nil {
		Init(nil)
	}
	errorLogger.Output(2, fmt.Sprintf(format, v...))
}

// Fatal logs fatal message and exits
func Fatal(v ...interface{}) {
	if errorLogger == nil {
		Init(nil)
	}
	errorLogger.Output(2, fmt.Sprint(v...))
	os.Exit(1)
}

// Fatalf logs formatted fatal message and exits
func Fatalf(format string, v ...interface{}) {
	if errorLogger == nil {
		Init(nil)
	}
	errorLogger.Output(2, fmt.Sprintf(format, v...))
	os.Exit(1)
}
