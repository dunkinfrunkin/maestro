package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
)

const defaultImage = "ghcr.io/dunkinfrunkin/maestro:latest"

func dockerAvailable() bool {
	return exec.Command("docker", "info").Run() == nil
}

func ensureImage(image string) error {
	out, _ := exec.Command("docker", "image", "inspect", image).CombinedOutput()
	if strings.Contains(string(out), "Error") || strings.Contains(string(out), "No such image") {
		fmt.Fprintf(os.Stderr, "Pulling %s...\n", image)
		cmd := exec.Command("docker", "pull", image)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		return cmd.Run()
	}
	return nil
}

func imageTag() string {
	if img := os.Getenv("MAESTRO_IMAGE"); img != "" {
		return img
	}
	if Version != "dev" {
		tag := Version
		if tag[0] != 'v' {
			tag = "v" + tag
		}
		return "ghcr.io/dunkinfrunkin/maestro:" + tag
	}
	return defaultImage
}

var envPassthrough = []string{
	"MAESTRO_SECRET",
	"MAESTRO_AUTH_DISABLED",
	"MAESTRO_OIDC_ISSUER",
	"MAESTRO_OIDC_CLIENT_ID",
	"MAESTRO_OIDC_CLIENT_SECRET",
	"MAESTRO_ENCRYPTION_KEY",
	"MAESTRO_FRONTEND_URL",
	"MAESTRO_WORKER_MODE",
	"ANTHROPIC_API_KEY",
	"OPENAI_API_KEY",
	"DATABASE_URL",
	"POSTGRES_HOST",
	"POSTGRES_PORT",
	"POSTGRES_DB",
	"POSTGRES_USER",
	"POSTGRES_PASSWORD",
}

func dockerRun(args []string, ports []string, extraEnv map[string]string, network string) error {
	if !dockerAvailable() {
		return fmt.Errorf("docker is not running — install Docker Desktop or start the daemon")
	}

	image := imageTag()
	if err := ensureImage(image); err != nil {
		return fmt.Errorf("failed to pull image: %w", err)
	}

	dockerArgs := []string{"run", "--rm", "-it"}

	for _, p := range ports {
		dockerArgs = append(dockerArgs, "-p", p)
	}

	for _, key := range envPassthrough {
		if val, ok := os.LookupEnv(key); ok {
			dockerArgs = append(dockerArgs, "-e", key+"="+val)
		}
	}
	for k, v := range extraEnv {
		dockerArgs = append(dockerArgs, "-e", k+"="+v)
	}

	if network != "" {
		dockerArgs = append(dockerArgs, "--network", network)
	}

	dockerArgs = append(dockerArgs, image)
	dockerArgs = append(dockerArgs, args...)

	cmd := exec.Command("docker", dockerArgs...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
