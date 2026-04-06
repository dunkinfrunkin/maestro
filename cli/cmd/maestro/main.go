package main

import (
	"os"

	"github.com/dunkinfrunkin/maestro/cli/cmd/maestro/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}
