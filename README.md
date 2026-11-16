# Markdown Editor

עורך טקסט מינימלי ב-Tkinter עם פאנל outline לכותרות markdown, מיזוג סקציות בשמירה, וסנכרון git מובנה.

## Features

- עורך טקסט עם undo/redo (Ctrl+Z / Ctrl+Y)
- פאנל צד שמציג את כל כותרות ה-markdown (# ו-##) וקופץ אליהן בלחיצה
- מיזוג היררכי של סקציות בשמירה: סקציות עם אותה כותרת מתאחדות, תתי-כותרות נשארות תחת ההורה הנכון
- סנכרון git (pull + commit + push) בלחיצת כפתור עם token
- ערכת צבעים כהה

## Requirements

- Python 3 עם tkinter
- git (לפיצ'ר הסנכרון)

tkinter לא תמיד מגיע עם python. התקנה לפי הפצה:

```bash
# Fedora / RHEL
sudo dnf install python3-tkinter
# Debian / Ubuntu
sudo apt install python3-tk
# Arch
sudo pacman -S tk
# openSUSE
sudo zypper install python3-tk
```

כל שאר התלויות (subprocess, threading, json, urllib) הן חלק מהספרייה הסטנדרטית ולא דורשות התקנה.

## Usage

```bash
python editor.py
```

## Git sync

כדי להשתמש בסנכרון, פתח קובץ שנמצא בתוך תיקיית git repo, הזן בתחתית החלון:

- token: GitHub personal access token עם הרשאת Contents: Read and write
- repo: כתובת ה-HTTPS של הריפו, למשל https://github.com/user/repo.git

ואז לחץ Pull+Push. הסטטוס מוצג ליד הכפתור.

## Files

- editor.py — התוכנה עצמה
- ~/.editor_git.json — נשמר אוטומטית, מכיל את ה-repo URL וה-token האחרונים (הרשאות 600)

## Security note

הקובץ ~/.editor_git.json שומר את ה-token בטקסט גלוי. הוא מוגבל להרשאות 600 (קריאה למשתמש בלבד), אבל לאבטחה טובה יותר עדיף להסתמך על git credential helper במקום. אל תעלה את הקובץ הזה ל-git.






```bash
cat > .gitignore << 'EOF'
.editor_git.json
__pycache__/
*.pyc
EOF
```


## Requirements

- Python 3 עם tkinter — לעורך עצמו
- git — רק לפיצ'ר הסנכרון (Pull+Push). העורך עובד בלעדיו.


# Fedora / RHEL
sudo dnf install git
# Debian / Ubuntu
sudo apt install git
# Arch
sudo pacman -S git


