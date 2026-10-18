# KogitechHub

Configuratore di mouse per Linux, con interfaccia scura ispirata a Logitech G HUB
(schema originale, nessun asset copiato). Pensato per Nobara/Fedora, costruito su
[libratbag](https://gitlab.freedesktop.org/libratbag/libratbag) tramite il demone `ratbagd`.

![KogitechHub](data/kogitechhub.svg)

## Funzioni

- **Dashboard** con tutti i mouse collegati: quelli supportati da libratbag sono configurabili,
  gli altri (es. un mouse HP qualunque) compaiono in sola lettura.
- **Slider dei preset DPI**:
  - **clic sulla barra** → aggiunge un preset in quel punto;
  - **clic sul numero** → apre un editor per **digitare il valore esatto** (Invio conferma, Esc annulla);
    il numero non trascina mai la barra;
  - **trascinamento del pallino** → cambia il valore e riordina da solo i preset;
  - **trascinamento del pallino lontano dalla barra + rilascio** → rimuove il preset;
  - **frecce ←/→** (o doppio clic sul valore nel pannello) → sposta il preset attivo.
- **Valore digitato**: rispettato quando il mouse lo supporta. Se il dispositivo ha una
  griglia di valori (per esempio il G402 accetta solo 252, 302, 352, 402, …, 1602, 3202) e il
  numero digitato non esiste, viene scritto il valore supportato più vicino e l'app lo dice con
  un avviso — scrivere un valore inesistente verrebbe **ignorato dal mouse** e la modifica
  sembrerebbe non funzionare.
- **Preset di avvio** (riquadro ambra): il DPI che il mouse usa all'accensione, modificabile.
- **Tasti DPI del mouse**: i preset restano in ordine crescente, quindi "DPI su" aumenta e
  "DPI giù" diminuisce. Le scelte fatte con i tasti fisici vengono rilette ogni ~2 secondi.
- **Frequenza di report** (125/250/500/1000 Hz, in base a ciò che il mouse dichiara).
- **Preset di fabbrica**: "Ripristina predefiniti" scrive 400/800/1600/3200 DPI con avvio a 800
  e frequenza massima; se il mouse ha una griglia diversa (G402: 402/802/1602/3202) usa i valori
  supportati più vicini, così la scrittura va a buon fine.
- Le impostazioni vengono scritte nella **memoria onboard** del mouse: restano attive anche
  senza KogitechHub e anche su un altro computer.

## Requisiti

- Linux con Python 3.10+
- PySide6 (Qt 6) per l'interfaccia
- PyGObject per il collegamento D-Bus a ratbagd
- `ratbagd` attivo (fa da ponte verso il mouse; nessun accesso diretto a `/dev/hidraw*`)

Funziona su qualunque distribuzione: **Fedora, Nobara, RHEL, Debian, Ubuntu, Linux Mint,
Pop!_OS, Mobian (Raspberry Pi), Arch, Manjaro, openSUSE, Gentoo**. Non servono `sudo`
per lanciarlo e nessuna regola udev.

## Installazione

Il modo più semplice su ogni distro è `./run.sh`: lo script controlla le dipendenze,
installa la voce nel menu e poi avvia l'app. Per installare prima i pacchetti:

| Distro | Comando |
|---|---|
| Fedora / Nobara / RHEL | `sudo dnf install python3-pyside6 python3-gobject libratbag-ratbagd` |
| Debian / Ubuntu / Mint / Mobian | `sudo apt install python3-pyside6 python3-gi ratbagd` |
| Arch / Manjaro | `sudo pacman -S python-pyside6 python-gobject ratbagd` |
| openSUSE | `sudo zypper install python3-pyside6 python3-gobject ratbagd` |

Se la tua distribuzione non ha PySide6 nei repository (comune su Debian/Ubuntu
e su ARM), installalo da pip:

```bash
pip install --user PySide6          # alternativa: python3-pyside6
```

Poi abilita il servizio una volta sola:

```bash
sudo systemctl enable --now ratbagd
```

### Verifica dell'ambiente

```bash
./run.sh --check        # oppure: python3 -m kogitechhub --check
```

Stampa distribuzione, versione di Python/Qt, PyGObject, stato di ratbagd, mouse trovati
e se la voce nel menu è installata, con il comando giusto per la tua distro se qualcosa
manca. Funziona anche senza interfaccia grafica (utile su server o via ssh).

## Avvio

```bash
./run.sh              # dalla cartella del progetto
./run.sh --mock       # prova l'interfaccia con mouse simulati, senza hardware
./run.sh --check      # verifica dipendenze e servizi, poi esce
```

Funziona sia su Wayland sia su X11, su Plasma, GNOME, Cinnamon, XFCE e desktop
simili: la voce nel menu è un file `.desktop` standard con l'icona del progetto.

Ad ogni avvio `run.sh` installa in modo idempotente la voce nelle applicazioni:
dopo la prima esecuzione **KogitechHub si trova nella ricerca con il tasto Super**
(menu Start), con l'icona del progetto. Nessun `sudo` richiesto:

- `~/.local/share/applications/kogitechhub.desktop` (con `Icon=` che punta
  all'SVG del progetto: l'icona non dipende dalla cache del tema)
- `~/.local/share/icons/hicolor/scalable/apps/kogitechhub.svg` e
  `~/.local/share/icons/hicolor/256x256/apps/kogitechhub.png` (stessa icona nel
  tema, per chi cerca l'app per nome)

Se sposti la cartella del progetto, riesegui `./run.sh` per aggiornare il percorso
memorizzato nella voce. Per toglierla:

```bash
rm ~/.local/share/applications/kogitechhub.desktop \
   ~/.local/share/icons/hicolor/scalable/apps/kogitechhub.svg \
   ~/.local/share/icons/hicolor/256x256/apps/kogitechhub.png
update-desktop-database ~/.local/share/applications
```

## Come funziona

```
QML (interfaccia)  <->  Controller (PySide6)  <->  Engine  <->  Backend
                                                                    |- ratbag    (D-Bus verso ratbagd: scrive)
                                                                    |- sysinput  (/proc/bus/input: sola lettura)
                                                                    '- mock      (--mock)
```

- Nessuna regola udev e nessun `sudo`: a scrivere sul mouse ci pensa `ratbagd`.
- Le modifiche vengono scritte ~0,35 s dopo l'ultimo gesto (o subito al rilascio del mouse);
  durante un trascinamento lungo si scrive comunque ogni ~0,6 s per dare un riscontro in tempo reale.
- Il numero di preset dipende dagli slot hardware del mouse (non è illimitato).

### Note tecniche sul backend ratbag

Tre dettagli di `ratbagd` (libratbag 0.18) che il backend rispetta:

1. `Capabilities` del G402 è `[2]`: `RATBAG_RESOLUTION_CAP_DISABLE = 2`
   (`SEPARATE_XY_RESOLUTION = 1`). Con il valore sbagliato ogni scrittura veniva respinta
   come "numero fisso di preset".
2. La proprietà `Resolution` è dichiarata di tipo **variant**, quindi va scritta con un
   variant annidato (`v(v(u))`, oppure `v(v((uu)))` con X/Y separati). Il tipo viene
   rilevato a runtime, quindi funziona anche con `ratbagd` più vecchi che la dichiarano `u`.
3. Le modifiche sono in staging: `Commit` sul dispositivo le scrive davvero sull'hardware.

## Test

```bash
PYTHONPATH=src dbus-run-session -- python3 -m unittest discover -s tests
```

Copre il modello dati, il rilevamento da `/proc/bus/input`, il controller, il
rilevamento della distribuzione (con `/etc/os-release` finti: Fedora, Debian, Ubuntu,
Mint, Mobian, Arch, openSUSE) e il backend ratbag contro un finto `ratbagd` su bus di
sessione (`KOGITECHHUB_BUS=session`).

## Problemi comuni

- Banner "KogitechHub non riesce a parlare con libratbag": `sudo systemctl enable --now ratbagd`.
- Un mouse appare in sola lettura: libratbag non lo supporta (`ratbagctl list` non lo elenca).
- I mouse wireless dietro un ricevitore (Unifying/Nano) non sono ancora configurabili.
- I valori DPI che il mouse accetta sono quelli che dichiara il dispositivo: digitandone
  uno diverso dal set supportato, l'app lo converte nel valore supportato più vicino e lo
  segnala (KogitechHub mostra sempre il valore che il dispositivo ha effettivamente memorizzato).

## Crediti

Ispirato a Logitech G HUB; basato su libratbag/ratbagd e Qt 6 (PySide6).
Tutti i grafica e il testo sono originali di questo progetto.
