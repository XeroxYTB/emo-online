//go:build windows

package main

import (
	"github.com/jchv/go-webview2/webview"
)

func showNativeUI(url string) {
	w := webview.New(false)
	if w == nil {
		openBrowser(url)
		select {}
	}
	defer w.Destroy()
	w.SetTitle("Émo Agent")
	w.SetSize(520, 820, webview.HintNone)
	w.Navigate(url)
	w.Run()
}
