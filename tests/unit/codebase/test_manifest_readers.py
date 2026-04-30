"""Unit tests for manifest readers."""

from __future__ import annotations

from pathlib import Path

from tech_scout.codebase.manifest_readers import (
    DotNetManifestReader,
    GoManifestReader,
    JavaManifestReader,
    NodeManifestReader,
    PythonManifestReader,
    RustManifestReader,
)
from tech_scout.domain.enums import StackKind


class TestPythonManifestReader:
    def test_claims_pyproject(self, tmp_path: Path) -> None:
        f = tmp_path / "pyproject.toml"
        f.write_text("[project]\nname = 'demo'", encoding="utf-8")
        reader = PythonManifestReader()
        assert reader.claims(f)

    def test_does_not_claim_unrelated(self, tmp_path: Path) -> None:
        f = tmp_path / "config.json"
        f.write_text("{}", encoding="utf-8")
        assert not PythonManifestReader().claims(f)

    def test_reads_pyproject_with_dependencies(self, tmp_path: Path) -> None:
        f = tmp_path / "pyproject.toml"
        f.write_text(
            """\
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "pydantic>=2.7",
    "langgraph>=0.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
""",
            encoding="utf-8",
        )
        result = PythonManifestReader().read(f)
        assert result.ecosystem == "python"
        assert result.language == "Python"
        assert result.language_version == ">=3.10"
        names = {dep.name for dep in result.dependencies}
        assert "fastapi" in names
        assert "pydantic" in names
        assert "langgraph" in names
        assert "pytest" in names
        # Dev marker
        pytest_dep = next(d for d in result.dependencies if d.name == "pytest")
        assert pytest_dep.is_dev
        # Classification
        fastapi = next(d for d in result.dependencies if d.name == "fastapi")
        assert fastapi.kind == StackKind.FRONTEND
        langgraph = next(d for d in result.dependencies if d.name == "langgraph")
        assert langgraph.kind == StackKind.AGENT_FRAMEWORK

    def test_reads_requirements_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text(
            "# Comment\nfastapi>=0.110\npydantic\n  redis==5.0\n",
            encoding="utf-8",
        )
        result = PythonManifestReader().read(f)
        names = {dep.name for dep in result.dependencies}
        assert "fastapi" in names
        assert "pydantic" in names
        assert "redis" in names
        redis_dep = next(d for d in result.dependencies if d.name == "redis")
        assert redis_dep.kind == StackKind.QUEUE


class TestNodeManifestReader:
    def test_reads_package_json(self, tmp_path: Path) -> None:
        f = tmp_path / "package.json"
        f.write_text(
            "{\n"
            '  "name": "demo",\n'
            '  "engines": {"node": ">=20"},\n'
            '  "dependencies": {\n'
            '    "next": "14.2.0",\n'
            '    "react": "18.2.0"\n'
            "  },\n"
            '  "devDependencies": {\n'
            '    "vitest": "1.5.0"\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        result = NodeManifestReader().read(f)
        assert result.language == "JavaScript/TypeScript"
        assert result.language_version == ">=20"
        names = {dep.name for dep in result.dependencies}
        assert "next" in names
        assert "vitest" in names
        next_dep = next(d for d in result.dependencies if d.name == "next")
        assert next_dep.kind == StackKind.FRONTEND
        vitest_dep = next(d for d in result.dependencies if d.name == "vitest")
        assert vitest_dep.is_dev
        assert vitest_dep.kind == StackKind.TEST_EVAL


class TestGoManifestReader:
    def test_reads_go_mod(self, tmp_path: Path) -> None:
        f = tmp_path / "go.mod"
        f.write_text(
            """\
module example.com/demo

go 1.22

require (
\tgithub.com/gin-gonic/gin v1.10.0
\tgo.mongodb.org/mongo-driver v1.15.0
\tgo.uber.org/zap v1.27.0 // indirect
)
""",
            encoding="utf-8",
        )
        result = GoManifestReader().read(f)
        assert result.language == "Go"
        assert result.language_version == "1.22"
        names = {dep.name for dep in result.dependencies}
        assert "github.com/gin-gonic/gin" in names
        assert "go.mongodb.org/mongo-driver" in names
        gin = next(d for d in result.dependencies if d.name == "github.com/gin-gonic/gin")
        assert gin.kind == StackKind.FRONTEND
        zap = next(d for d in result.dependencies if d.name == "go.uber.org/zap")
        assert zap.is_dev
        assert zap.kind == StackKind.OBSERVABILITY


class TestRustManifestReader:
    def test_reads_cargo_toml(self, tmp_path: Path) -> None:
        f = tmp_path / "Cargo.toml"
        f.write_text(
            """\
[package]
name = "demo"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = "1.0"
axum = "0.7"

[dev-dependencies]
tokio-test = "0.4"
""",
            encoding="utf-8",
        )
        result = RustManifestReader().read(f)
        names = {dep.name for dep in result.dependencies}
        assert "tokio" in names
        assert "axum" in names
        axum_dep = next(d for d in result.dependencies if d.name == "axum")
        assert axum_dep.kind == StackKind.FRONTEND


class TestJavaManifestReader:
    def test_reads_gradle(self, tmp_path: Path) -> None:
        f = tmp_path / "build.gradle"
        f.write_text(
            """\
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:3.2.0'
    implementation 'org.postgresql:postgresql:42.6.0'
    testImplementation 'junit:junit:4.13.2'
}
""",
            encoding="utf-8",
        )
        result = JavaManifestReader().read(f)
        names = {dep.name for dep in result.dependencies}
        assert "org.springframework.boot:spring-boot-starter-web" in names
        assert "org.postgresql:postgresql" in names


class TestDotNetManifestReader:
    def test_reads_csproj(self, tmp_path: Path) -> None:
        f = tmp_path / "Demo.csproj"
        f.write_text(
            """\
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.App" Version="8.0.0" />
    <PackageReference Include="Serilog" Version="3.1.0" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        result = DotNetManifestReader().read(f)
        assert result.language_version == "net8.0"
        names = {dep.name for dep in result.dependencies}
        assert "Microsoft.AspNetCore.App" in names
        assert "Serilog" in names
