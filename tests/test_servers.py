"""Tests for Part 2 Stage 3: Server User Data and Launch Scripts."""

from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SERVER_SCRIPTS_DIR = SCRIPTS_DIR / "server_scripts"


def test_jenkins_userdata_script():
    """Verify jenkins_userdata.sh installs Java 21, Docker, AWS CLI, and configures permissions."""
    script_path = SERVER_SCRIPTS_DIR / "jenkins_userdata.sh"
    assert script_path.exists(), "jenkins_userdata.sh must exist"

    content = script_path.read_text(encoding="utf-8")
    assert "openjdk-21-jre" in content, "Must install Java 21 for Jenkins"
    assert "docker.io" in content, "Must install Docker"
    assert "pkg.jenkins.io" in content, "Must configure official Jenkins repository"
    assert "awscli-exe-linux-x86_64.zip" in content, "Must install AWS CLI v2"
    assert "usermod -aG docker jenkins" in content, "Must add jenkins user to docker group"


def test_app_userdata_deploy_script():
    """Verify app_userdata.sh sets up /opt/auditpilot/deploy.sh with Secrets Manager and CloudWatch."""
    script_path = SERVER_SCRIPTS_DIR / "app_userdata.sh"
    assert script_path.exists(), "app_userdata.sh must exist"

    content = script_path.read_text(encoding="utf-8")
    assert "/opt/auditpilot/deploy.sh" in content, "Must write deploy.sh"
    assert "aws secretsmanager get-secret-value" in content, "Must read secret from Secrets Manager"
    assert "auditpilot/google_api_key" in content, "Must target auditpilot/google_api_key"
    assert "awslogs-group=auditpilot" in content, "Must ship logs to CloudWatch log group"
    assert "curl -fs http://localhost/health" in content, "Must verify container health"
    assert "__REGION__" in content and "__ACCOUNT__" in content, "Must use placeholders for region and account"


def test_launch_servers_script_structure():
    """Verify launch_servers.sh resolves AMIs and launches instances with correct profiles."""
    script_path = SCRIPTS_DIR / "launch_servers.sh"
    assert script_path.exists(), "launch_servers.sh must exist"

    content = script_path.read_text(encoding="utf-8")
    assert "auditpilot_jenkins" in content, "Must tag Jenkins server"
    assert "auditpilot_app" in content, "Must tag App server"
    assert "t3.medium" in content, "Jenkins must be t3.medium"
    assert "t3.small" in content, "App server must be t3.small"
    assert "auditpilot_jenkins_profile" in content, "Must use Jenkins instance profile"
    assert "auditpilot_app_profile" in content, "Must use App instance profile"
