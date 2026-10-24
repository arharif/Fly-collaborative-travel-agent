# FLY — Visual themes and branding 🌸 🖤 🌿

The [interactive Academy](https://arharif.github.io/Fly-collaborative-travel-agent/) offers three themes:

- **Rose 🌸** — default soft-pink travel-studio appearance
- **Onyx Black 🖤** — dark, restrained interface
- **King Green 🌿** — deep emerald palette

Use the **Theme** control on the website header to switch. Your selection is saved in this browser. The site supports reduced-motion system settings. Themes are controlled by `docs/assets/themes.css` and `docs/assets/themes.js`; the GitHub README is Markdown, so it cannot run theme-switcher JavaScript.

## Author attribution

The Academy footer and README include a link to **[@arharif — About X1](https://arharif.github.io/about-x1)**.

## GitHub publishing

1. Extract the complete project ZIP.
2. Open your GitHub repository **arharif/Fly-collaborative-travel-agent**.
3. Upload/replace files from the extracted folder, preserving directory structure (especially `docs/assets/`).
4. Confirm GitHub Pages is configured to publish from `main` → `/docs`.
5. Refresh the published website and test all three themes on desktop and mobile. For stubborn cached styles, force-refresh or use a private tab.

The standalone `FLY_Animated_Tutorial_UPDATED.html` includes theme CSS/JS inline and can be opened locally without the project folder. Do not edit it instead of the site's `docs/index.html`.

## Safety

Do not commit AWS credentials, Hugging Face access tokens, private `.env` files, or output files containing secrets. Keep application credentials in Hugging Face Space Secrets. The static tutorial is separate from the Python chatbot runtime.
