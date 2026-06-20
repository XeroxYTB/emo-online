//go:build !windows

package main

func showNativeUI(url string) {
	openBrowser(url)
	select {}
}
