![icon](editor.png)
# Markdown Editor

עורך טקסט מינימלי ב-Tkinter עם פאנל outline לכותרות markdown, מיזוג סקציות בשמירה, וסנכרון git מובנה.

## Features

- עורך טקסט עם undo/redo (Ctrl+Z / Ctrl+Y)
- פאנל צד שמציג את כל כותרות ה-markdown (# ו-##) וקופץ אליהן בלחיצה
- מיזוג היררכי של סקציות בשמירה: סקציות עם אותה כותרת מתאחדות, תתי-כותרות נשארות תחת ההורה הנכון
- סנכרון git (pull + commit + push) בלחיצת כפתור עם token
- ערכת צבעים כהה

## Requirements

- Python 3 עם tkinter — לעורך עצמו
- git — רק לפיצ'ר הסנכרון (Pull+Push). העורך עובד בלעדיו.

tkinter לא תמיד מגיע עם python. התקנה לפי הפצה:

```bash
# tkinter
sudo dnf install python3-tkinter     # Fedora / RHEL
sudo apt install python3-tk          # Debian / Ubuntu
sudo pacman -S tk                    # Arch
sudo zypper install python3-tk       # openSUSE

# git
sudo dnf install git                 # Fedora / RHEL
sudo apt install git                 # Debian / Ubuntu
sudo pacman -S git                   # Arch
```

כל שאר התלויות (subprocess, threading, json, urllib) הן חלק מהספרייה הסטנדרטית.

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

הקובץ ~/.editor_git.json שומר את ה-token בטקסט גלוי. הוא מוגבל להרשאות 600 (קריאה למשתמש בלבד), אבל לאבטחה טובה יותר עדיף להסתמך על git credential helper. אל תעלה אותו ל-git:

```bash
cat > .gitignore << 'EOF'
.editor_git.json
__pycache__/
*.pyc
EOF
```

## Development

פקודות לפרופיילינג, בנייה ובדיקות עומס.

### memory profile

מדידת RSS ו-CPU לאורך ריצה, עם גרף:

```bash
pip install matplotlib psrecord
psrecord "python3 ./editor.py" --interval 1 --log mem.txt --plot plot.png
```

חלופה בלי תלויות, קריאה ישירה מ-/proc (מומלץ, אמין יותר):

```bash
pid=$(pgrep -f "python.*editor.py" | head -1)
while kill -0 "$pid" 2>/dev/null; do
    ts=$(date +%T)
    read cpu mem <<<"$(ps -p "$pid" -o %cpu=,%mem=)"
    rss=$(awk '/VmRSS/{print $2/1024" MB"}' /proc/$pid/status)
    printf "%s  cpu=%s%%  mem=%s%%  rss=%s\n" "$ts" "$cpu" "$mem" "$rss"
    sleep 1
done
```

### build binary

בניית בינארי עצמאי:

```bash
sudo dnf install binutils
pip install pyinstaller
pyinstaller --onefile editor.py
ldd dist/editor
```

הערה: --onefile לא יוצר בינארי סטטי. python והספריות נארזים ב-archive שנפרש ל-/tmp בזמן ריצה, ו-ldd עדיין יראה תלות ב-libc של המערכת. בתוך toolbox/distrobox הרץ את הבנייה ואת ldd באותו container, אחרת הבינארי ייקשר ל-libs של סביבה אחרת.

### stress test

יצירת קובץ ענק עם כותרות ותתי-כותרות לבדיקת פאנל ה-outline תחת עומס:

```bash
awk 'BEGIN{for(i=1;i<=1000000;i++){m=i%50; if(m==0)printf "# Heading %d\n",i; else if(m==25)printf "## Sub %d\n",i; else printf "line %d lorem ipsum dolor sit amet consectetur adipiscing elit %d\n",i,i*7}}' > big.txt
wc -l big.txt
du -h big.txt
```

## License

MIT — see [LICENSE](LICENSE).
