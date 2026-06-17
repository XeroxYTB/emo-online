package main

import (
	"bytes"
	"encoding/json"
	"os"
)

var configMagic = []byte("\nEMOAGENTCFG\n")

type embeddedConfig struct {
	Token   string `json:"token"`
	Backend string `json:"backend"`
}

func readEmbeddedConfig() embeddedConfig {
	var cfg embeddedConfig
	exe, err := os.Executable()
	if err != nil {
		return cfg
	}
	data, err := os.ReadFile(exe)
	if err != nil {
		return cfg
	}
	idx := bytes.LastIndex(data, configMagic)
	if idx < 0 {
		return cfg
	}
	_ = json.Unmarshal(data[idx+len(configMagic):], &cfg)
	return cfg
}
