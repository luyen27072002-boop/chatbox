Góc nhỏ cuộc sống – V10 patch

Included updates:
1. Added language switcher (Vietnamese / English / 简体中文 / 繁體中文).
2. UI text updates when switching language.
3. Chat request now sends language to backend so AI replies in the selected language.
4. Added support for Simplified and Traditional Chinese at backend prompt + safety messages.
5. Moved pronoun selector to top bar and kept it synced with UI copy.
6. Visual polish: integrated logo, larger typography, livelier icon cards, styled toolbar selects, softer shadows.

How to apply:
- Put templates/index.html into your templates folder.
- Put static/app.js, static/styles.css, static/icons/brand-logo.png into your static folder.
- Replace app.py, ai_service.py, prompting.py, safety.py in your backend.
