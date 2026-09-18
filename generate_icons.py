import os
from pathlib import Path
from PIL import Image

SOURCE_IMAGE = Path(r"C:\Users\Sandeep Khadka\.gemini\antigravity\brain\70065041-a6d2-4acb-bf48-945b9569b8af\sonance_minimal_headphones_clean_1789707212196.jpg")
ROOT_DIR = Path(__file__).parent.resolve()

def generate_all_icons():
    if not SOURCE_IMAGE.exists():
        print(f"Error: Source image {SOURCE_IMAGE} not found!")
        return

    img = Image.open(SOURCE_IMAGE).convert("RGBA")
    print(f"Loaded source image: {img.size}")

    # Ensure target directories exist
    assets_dir = ROOT_DIR / "assets"
    ui_dir = ROOT_DIR / "ui"
    res_dir = ROOT_DIR / "android" / "app" / "src" / "main" / "res"

    assets_dir.mkdir(parents=True, exist_ok=True)
    ui_dir.mkdir(parents=True, exist_ok=True)

    # 1. Main high-res PNGs
    logo_1024 = img.resize((1024, 1024), Image.Resampling.LANCZOS)
    logo_1024.save(assets_dir / "logo.png", "PNG", optimize=True)
    print(f"Saved: {assets_dir / 'logo.png'}")

    icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    icon_512.save(assets_dir / "icon.png", "PNG", optimize=True)
    print(f"Saved: {assets_dir / 'icon.png'}")

    # 2. Web UI Assets
    logo_ui = img.resize((256, 256), Image.Resampling.LANCZOS)
    logo_ui.save(ui_dir / "logo.png", "PNG", optimize=True)
    print(f"Saved: {ui_dir / 'logo.png'}")

    fav_sizes = [(16, 16), (32, 32), (48, 48)]
    img.save(ui_dir / "favicon.ico", format="ICO", sizes=fav_sizes)
    print(f"Saved: {ui_dir / 'favicon.ico'}")

    # 3. Windows Multi-Resolution ICO & macOS ICNS
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(assets_dir / "icon.ico", format="ICO", sizes=ico_sizes)
    print(f"Saved: {assets_dir / 'icon.ico'}")

    try:
        img.save(assets_dir / "icon.icns", format="ICNS")
        print(f"Saved: {assets_dir / 'icon.icns'}")
    except Exception as e:
        print(f"Could not generate ICNS: {e}")

    # 4. Android Mipmap Launcher Icons
    android_densities = {
        "mipmap-mdpi": (48, 48),
        "mipmap-hdpi": (72, 72),
        "mipmap-xhdpi": (96, 96),
        "mipmap-xxhdpi": (144, 144),
        "mipmap-xxxhdpi": (192, 192),
    }

    for folder_name, size in android_densities.items():
        density_dir = res_dir / folder_name
        density_dir.mkdir(parents=True, exist_ok=True)
        target_icon = density_dir / "ic_launcher.png"
        resized = img.resize(size, Image.Resampling.LANCZOS)
        resized.save(target_icon, "PNG", optimize=True)
        print(f"Saved Android Icon [{folder_name}]: {target_icon} ({size[0]}x{size[1]})")

    print("All icons successfully generated across all platforms!")

if __name__ == "__main__":
    generate_all_icons()
