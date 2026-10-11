"""تست بسته‌بندی اندروید و قرارداد ساخت APK.

هدف: خرابی‌های ساکتی که فقط موقع ساخت روی گیت‌هاب معلوم می‌شوند اینجا گرفته
شوند — شناسه‌ی بسته‌ی نامعتبر، پوشه‌ی وب اشتباه، نبودِ gradle wrapper، مبدأ API
جاافتاده در اپ بومی، و مسیر خروجی APK که با مسیر آپلود در workflow نمی‌خواند.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from _helpers import ROOT

ANDROID = ROOT / "android"
WORKFLOW = ROOT / ".github" / "workflows" / "android.yml"


@pytest.fixture(scope="module")
def capacitor_config():
    return json.loads((ROOT / "capacitor.config.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


# --- تنظیمات Capacitor -----------------------------------------------------------


def test_app_id_is_a_valid_android_package(capacitor_config):
    app_id = capacitor_config["appId"]
    # نام بسته باید معکوس دامنه باشد؛ خط تیره و شماره‌ی ابتدایی مجاز نیست
    assert re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", app_id), app_id
    assert not app_id.startswith("com.example"), "شناسه‌ی نمونه نباید در بیلد بماند"


def test_web_directory_points_at_the_real_frontend(capacitor_config):
    assert capacitor_config["webDir"] == "web"
    assert (ROOT / capacitor_config["webDir"] / "index.html").is_file()
    assert capacitor_config["appName"] == "EXCHANCE"


def test_android_package_matches_capacitor_config(capacitor_config):
    gradle = (ANDROID / "app" / "build.gradle").read_text(encoding="utf-8")
    assert f'applicationId "{capacitor_config["appId"]}"' in gradle
    assert f'namespace = "{capacitor_config["appId"]}"' in gradle


def test_android_project_has_a_buildable_skeleton():
    assert (ANDROID / "settings.gradle").is_file()
    assert (ANDROID / "app" / "build.gradle").is_file()
    assert (ANDROID / "gradlew").is_file()
    assert (ANDROID / "gradle" / "wrapper" / "gradle-wrapper.jar").stat().st_size > 0

    props = (ANDROID / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text(encoding="utf-8")
    assert "distributionUrl=https" in props and "gradle-" in props


def test_manifest_requests_the_internet_and_uses_the_launcher_icon():
    manifest = (ANDROID / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'android:name="android.permission.INTERNET"' in manifest
    assert 'android:icon="@mipmap/ic_launcher"' in manifest
    assert 'android:roundIcon="@mipmap/ic_launcher_round"' in manifest
    assert "com.exchance.app" in manifest or "${applicationId}" in manifest


def test_launcher_icons_and_splash_exist_for_every_density():
    res = ANDROID / "app" / "src" / "main" / "res"
    assert (res / "mipmap-anydpi-v26" / "ic_launcher.xml").is_file()
    assert (res / "mipmap-xxxhdpi" / "ic_launcher.png").stat().st_size > 1000
    assert (res / "drawable-port-xxxhdpi" / "splash.png").stat().st_size > 1000


# --- مبدأ API در اپ بومی ----------------------------------------------------------


def test_config_js_is_loaded_before_the_app_script():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert html.index("/config.js") < html.index("/app.js"), "config.js باید قبل از app.js بیاید"


def test_config_js_resolves_a_native_api_base():
    config = (ROOT / "web" / "config.js").read_text(encoding="utf-8")
    assert "isNativePlatform" in config
    assert "window.API_BASE" in config
    assert re.search(r'DEPLOYED_API\s*=\s*"https://[^"]+"', config)


def test_every_api_call_goes_through_the_base_helper():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "const api = (path) => API_BASE + path;" in js
    raw = re.findall(r'fetch\(\s*[`"]/api/', js)
    assert raw == [], f"این درخواست‌ها مبدأ اپ بومی را نادیده می‌گیرند: {raw}"
    assert len(re.findall(r"fetch\(api\(", js)) == 4


def test_service_worker_precaches_the_new_config_file():
    sw = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    assert '"/config.js",' in sw


# --- حذف کامل هوش مصنوعی ----------------------------------------------------------


def test_ai_feature_is_gone_from_the_project():
    assert not (ROOT / "api" / "ai_chat.py").exists()
    assert not (ROOT / "lib" / "ai_provider.py").exists()
    assert not (ROOT / "tests" / "test_ai_provider.py").exists()

    watched = [ROOT / "vercel.json", ROOT / ".env.example", ROOT / "README.md"]
    for folder in ("api", "lib", "tests", "web"):
        watched.extend(sorted((ROOT / folder).glob("*")))
    watched = [p for p in watched if p.name != Path(__file__).name]

    offenders = []
    for path in watched:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "ai_chat" in text or "ai_provider" in text or "AI_API_KEY" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"ردپای هوش مصنوعی مانده است: {offenders}"


# --- workflow ساخت APK ----------------------------------------------------------


def test_workflow_builds_and_uploads_the_apk(workflow):
    yaml_text = WORKFLOW.read_text(encoding="utf-8")

    # «on» در YAML می‌تواند boolean شود؛ متن خام مطمئن‌تر است
    assert "workflow_dispatch:" in yaml_text
    assert "branches: [main]" in yaml_text

    job = workflow["jobs"]["build-apk"]
    assert job["runs-on"] == "ubuntu-latest"

    steps = job["steps"]
    uses = [s.get("uses", "") for s in steps if s.get("uses")]
    assert all("@" in u for u in uses), f"نسخه‌ی action ها پین نشده: {uses}"

    runs = "\n".join(s.get("run", "") for s in steps)
    assert "npm ci" in runs
    assert "npx cap sync android" in runs
    assert "./gradlew assembleDebug" in runs

    build = next(s for s in steps if "assembleDebug" in (s.get("run") or ""))
    assert build.get("working-directory") == "android"

    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload["with"]["path"] == "android/app/build/outputs/apk/debug/*.apk"
    assert upload["with"]["if-no-files-found"] == "error"


def test_workflow_can_actually_install_and_sync():
    # npm ci بدون lockfile کار نمی‌کند؛ cap sync هم به تنظیمات Capacitor نیاز دارد
    assert (ROOT / "package-lock.json").is_file()
    assert (ROOT / "capacitor.config.json").is_file()
    assert (ROOT / "package.json").is_file()

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["dependencies"]["@capacitor/android"]
    assert package["devDependencies"]["@capacitor/cli"]


def test_tag_push_publishes_a_github_release(workflow):
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in raw, "تگ نسخه باید workflow را اجرا کند"
    assert workflow["permissions"]["contents"] == "write", "ساخت Release نیاز به دسترسی نوشتن دارد"

    steps = workflow["jobs"]["build-apk"]["steps"]
    release = next(s for s in steps if s.get("uses", "").startswith("softprops/action-gh-release"))
    assert release["with"]["fail_on_unmatched_files"] is True
    assert "RELEASE_ASSET" in release["with"]["files"]
    assert release["with"]["generate_release_notes"] is True
    # فقط روی تگ اجرا شود، نه روی هر push به main
    assert release["if"] == "startsWith(github.ref, 'refs/tags/v')"


def test_release_asset_is_built_from_the_apk_gradle_just_made(workflow):
    steps = workflow["jobs"]["build-apk"]["steps"]
    namer = next(s for s in steps if s.get("name") == "Name the release asset")
    assert "${GITHUB_REF_NAME#v}" in namer["run"], "نسخه باید از نام تگ بیاید"
    assert "android/app/build/outputs/apk/debug/app-debug.apk" in namer["run"]
    assert "RELEASE_ASSET=" in namer["run"] and "GITHUB_ENV" in namer["run"]
    assert namer["if"] == "startsWith(github.ref, 'refs/tags/v')"


def test_release_tag_drives_the_in_app_version():
    gradle = (ANDROID / "app" / "build.gradle").read_text(encoding="utf-8")
    assert 'System.getenv("APP_VERSION") ?: "1.0"' in gradle

    build = next(s for s in yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
                 ["build-apk"]["steps"] if "assembleDebug" in (s.get("run") or ""))
    assert "github.ref_name" in build["env"]["APP_VERSION"]


def test_release_apk_path_matches_what_gradle_writes(workflow):
    # مسیر artifact و مسیر پیوست Release باید همان خروجی گریدل باشند
    steps = workflow["jobs"]["build-apk"]["steps"]
    artifact = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert artifact["with"]["path"] == "android/app/build/outputs/apk/debug/*.apk"


def test_workflow_paths_filter_matches_real_directories(workflow):
    # روی push، فیلتر مسیرها باید پوشه‌های واقعی را نام ببرد
    raw = WORKFLOW.read_text(encoding="utf-8")
    for entry in ("web/**", "android/**", "resources/**"):
        assert entry in raw
        assert (ROOT / entry.split("/")[0]).is_dir(), entry


def test_gitignore_keeps_build_outputs_and_secrets_out():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in ignored
    assert ".env" in ignored
    android_ignored = (ANDROID / ".gitignore").read_text(encoding="utf-8")
    for entry in (".gradle/", "build/", "local.properties", "app/src/main/assets/public"):
        assert entry in android_ignored, entry
