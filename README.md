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
- **Valore digitato rispettato**: 1600 resta 1600. Lo snappamento alla griglia del
  dispositivo vale solo per il trascinamento e per i valori suggeriti.
- **Preset di avvio** (riquadro ambra): il DPI che il mouse usa all'accensione, modificabile.
- **Tasti DPI del mouse**: i preset restano in ordine crescente, quindi "DPI su" aumenta e
  "DPI giù" diminuisce. Le scelte fatte con i tasti fisici vengono rilette ogni ~2 secondi.
- **Frequenza di report** (125/250/500/1000 Hz, in base a ciò che il mouse dichiara).
- **Preset di fabbrica**: "Ripristina predefiniti" scrive 400/800/1600/3200 DPI con avvio a 800
  e frequenza massima.
- Le impostazioni vengono scritte nella **memoria onboard** del mouse: restano attive anche
  senza KogitechHub e anche su un altro computer.

## Requisiti

- Python 3.10+
- PySide6 (Qt 6) e PyGObject
- `ratbagd` attivo (fa da ponte verso il mouse; nessun accesso diretto a `/dev/hidraw*`)

## Installazione (Nobara / Fedora)

```bash
sudo dnf install python3-pyside6 python3-gobject libratbag-ratbagd
sudo systemctl enable --now ratbagd
```

Se `dnf` non trova `python3-pyside6`: `pip install --user PySide6`.

## Avvio

```bash
./run.sh              # dalla cartella del progetto
./run.sh --mock       # prova l'interfaccia con mouse simulati, senza hardware
```

Installazione nel menu applicazioni (opzionale):

```bash
pip install --user --no-deps .
install -Dm644 data/kogitechhub.desktop ~/.local/share/applications/kogitechhub.desktop
install -Dm644 data/kogitechhub.svg ~/.local/share/icons/hicolor/scalable/apps/kogitechhub.svg
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

Copre il modello dati, il rilevamento da `/proc/bus/input`, il controller e il backend
ratbag contro un finto `ratbagd` su bus di sessione (`KOGITECHHUB_BUS=session`).

## Problemi comuni

- Banner "KogitechHub non riesce a parlare con libratbag": `sudo systemctl enable --now ratbagd`.
- Un mouse appare in sola lettura: libratbag non lo supporta (`ratbagctl list` non lo elenca).
- I mouse wireless dietro un ricevitore (Unifying/Nano) non sono ancora configurabili.
- I valori DPI che il mouse accetta sono quelli che dichiara il dispositivo: digitandone
  uno diverso dal set supportato, il mouse può arrotondarlo (KogitechHub mostra sempre
  il valore che il dispositivo ha effettivamente memorizzato).

## Crediti

Ispirato a Logitech G HUB; basato su libratbag/ratbagd e Qt 6 (PySide6).
Tutti i grafica e il testo sono originali di questo progetto.
