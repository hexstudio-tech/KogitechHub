# KogitechHub

Configuratore di periferiche per Linux, con interfaccia scura ispirata a Logitech G HUB
(schema originale, nessun asset copiato). Pensato per Nobara/Fedora, costruito su tre
progetti open source:

- [libratbag](https://gitlab.freedesktop.org/libratbag/libratbag) (`ratbagd`) per i **mouse**: DPI, preset, frequenza;
- [OpenRGB](https://openrgb.org/) per l'**illuminazione RGB** di tastiere, cuffie e altri dispositivi: colori, modalità/pattern, luminosità, velocità;
- [HeadsetControl](https://github.com/Sapd/HeadsetControl) per le **cuffie USB**: batteria, sidetone, luci, spegnimento automatico, chatmix.

![KogitechHub](data/kogitechhub.svg)

## Funzioni

### Dashboard

- Un'unica schermata con tutti i dispositivi collegati, ognuno come scheda con il suo
  tipo (mouse, tastiera, cuffia, altro RGB): un clic apre la pagina adatta.
- **Rilevamento di sistema** di ciò che i backend non conoscono: legge
  `/proc/bus/input/devices` (USB e Bluetooth) e le porte seriali `/dev/ttyACM*`,
  `/dev/ttyUSB*`, unendo le interfacce multiple dello stesso dispositivo. Una tastiera
  cablata generica compare quindi sempre, in sola lettura se nessun backend sa
  controllarne l'RGB (con il motivo scritto nella scheda).

### Tastiere, cuffie e RGB (OpenRGB)

- **Modalità/pattern** dichiarati dal dispositivo (Direct, Static, Breathing, Rainbow,
  Spectrum Cycle, Wave...): quella attiva è quella che il dispositivo riporta.
- **Colore** (tavolozza + campo esadecimale), **luminosità** e **velocità** degli effetti,
  scritti sul controller RGB del dispositivo.
- OpenRGB non comunica colori e velocità correnti: l'app mostra gli ultimi valori
  applicati da KogitechHub e li ricorda tra un avvio e l'altro.
- Le cuffie riconosciute da OpenRGB hanno una pagina RGB; le stesse cuffie possono
  comparire anche come dispositivo HeadsetControl con i controlli della cuffia.

### Laboratorio HID (tastiere e periferiche non riconosciute)

Quando OpenRGB non conosce un dispositivo, KogitechHub può comunque parlargli
attraverso il canale del kernel che lo raggiunge davvero: i nodi `/dev/hidraw*`.

- **Apri laboratorio HID** dalla scheda in sola lettura: elenca le interfacce del
  dispositivo con i report che dichiarano (tipo, ID, byte, usage page) e propone per
  prima quella di configurazione, cioè quella con report `feature`/`output` su pagina
  vendor (`0xFF00` e simili).
- **Abilita accesso**: installa la regola udev `TAG+="uaccess"` per quel VID/PID
  (chiede la password) e ricarica le regole; senza, quel nodo resta illegibile.
- **Avvia** cattura i report in arrivo e li mostra in tempo reale (una tastiera invia
  anche i tasti premuti: ferma la cattura prima di digitare password).
- **Salva** scrive la cattura in JSONL sotto `~/.local/share/kogitechhub/captures/`,
  con l'intestazione del dispositivo, così si può confrontare una prova con l'altra.
- **leggi feature id N**: legge (solo lettura) un report feature dichiarato. È lo stato
  corrente del dispositivo: cambiando effetto dai tasti della tastiera e rileggendo si
  vede quali byte cambiano.
- **Invia un report**: hex più `output`/`feature`, per replicare da Linux quello che fa
  il software del produttore. Un report sbagliato si annulla con un altro report (al
  massimo si ricollega la periferica).

Le stesse operazioni da terminale, con `scripts/hid_sniff.py`:

```bash
scripts/hid_sniff.py list                                    # nodi hidraw, permessi, report
scripts/hid_sniff.py info /dev/hidraw2                       # descrittore e report dichiarati
scripts/hid_sniff.py grant 258a 002a                         # regola udev per l'accesso
scripts/hid_sniff.py capture /dev/hidraw2 --seconds 30 --out prova.jsonl
scripts/hid_sniff.py read /dev/hidraw2 --report 9 --length 504
scripts/hid_sniff.py send /dev/hidraw2 "05 01 FF 00 00" --type feature
```

Ricostruire il protocollo è un lavoro di deduzione: la cattura mostra la firma dei
comandi, la lettura mostra lo stato. KogitechHub non inventa comandi per conto suo,
mostra solo quello che il dispositivo dichiara e risponde.

### Cuffie USB (HeadsetControl)

- **Batteria** e stato di carica, **chatmix** (bilanciamento gioco/chat).
- **Sidetone** (0–128), **LED** on/off, **spegnimento automatico** (mai/10/30/60 min),
  mostrati solo se la cuffia dichiara la funzione.

### Mouse (libratbag)

- I mouse supportati da libratbag sono configurabili; gli altri (es. un mouse HP qualunque)
  compaiono in sola lettura con le loro informazioni.
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
- **OpenRGB** (facoltativo) per l'RGB di tastiere e cuffie
- **HeadsetControl** (facoltativo) per batteria, sidetone e luci delle cuffie

Funziona su qualunque distribuzione: **Fedora, Nobara, RHEL, Debian, Ubuntu, Linux Mint,
Pop!_OS, Mobian (Raspberry Pi), Arch, Manjaro, openSUSE, Gentoo**. Non servono `sudo`
per lanciarlo. Le regole udev servono solo dove il pacchetto OpenRGB non le installa già
(`openrgb --generate-udev-rules`, oppure `--print-udev-rules | sudo tee /etc/udev/rules.d/60-openrgb.rules`).

## Installazione

Non serve installare niente a mano: scarica la cartella e lancia

```bash
./run.sh
```

`run.sh` installa la voce nel menu, controlla le dipendenze e, se manca qualcosa,
chiede **Y/N** per ogni pacchetto prima di installarlo con il gestore della tua
distribuzione (`apt`, `dnf`, `pacman`, `zypper`, `apk`, `xbps`, `emerge`), usando
`sudo`. Le dipendenze controllate sono:

| Dipendenza | A cosa serve | Se manca |
|---|---|---|
| Python 3.10+ | eseguire l'app | `run.sh` propone di installarlo |
| PySide6 / Qt 6 | interfaccia grafica | pacchetto della distro; se non esiste, venv locale + pip |
| PyGObject | collegamento D-Bus a ratbagd | pacchetto della distro (`python3-gi`, `python3-gobject`, ...) |
| ratbagd (libratbag) | scrivere le impostazioni sul mouse | pacchetto + `systemctl enable ratbagd` |
| OpenRGB | RGB di tastiere e cuffie | pacchetto della distro (`openrgb`) |
| HeadsetControl | batteria, sidetone e luci delle cuffie | pacchetto della distro (`headsetcontrol`) |

Se rispondi `N` l'app parte lo stesso quando è possibile (senza PySide6 non può
partire, senza ratbagd resta in sola lettura) e ti viene ricordato il comando da
eseguire. Sui sistemi dove PySide6 non è nei repository, l'installer crea una
cartella locale `.venv/` con `pip` e la usa al posto del Python di sistema, senza
toccare il resto della distribuzione.

Altre opzioni:

```bash
./run.sh --install-deps     # installa solo le dipendenze, poi esce
./run.sh --yes              # risponde sì a tutte le domande (installazione automatica)
./run.sh --no-install       # non installa nulla: spiega solo cosa manca
./run.sh --check            # diagnostica completa, non installa nulla
```

Installazione manuale, se preferisci i pacchetti di sistema:

| Distro | Comando |
|---|---|
| Fedora / Nobara / RHEL | `sudo dnf install python3-pyside6 python3-gobject libratbag-ratbagd openrgb headsetcontrol` |
| Debian / Ubuntu / Mint / Mobian | `sudo apt install python3-pyside6 python3-gi ratbagd openrgb headsetcontrol` |
| Arch / Manjaro | `sudo pacman -S python-pyside6 python-gobject ratbagd openrgb` poi `yay -S headsetcontrol` (AUR) |
| openSUSE | `sudo zypper install python3-pyside6 python3-gobject ratbagd openrgb headsetcontrol` |

Su Arch/Manjaro `headsetcontrol` è solo su AUR: l'installer propone `pacman`, che
fallisce, e spiega di usare `yay` o `paru`. Su Debian/Ubuntu il pacchetto piu recente
arriva dal PPA di HeadsetControl.

Se la tua distribuzione non ha PySide6 nei repository (comune su Debian/Ubuntu
e su ARM), installalo da pip:

```bash
pip install --user PySide6          # alternativa: python3-pyside6
```

E abilita il servizio una volta sola (spesso non serve: ratbagd viene avviato
su richiesta via D-Bus):

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
./run.sh                    # dalla cartella del progetto
./run.sh --mock             # prova l'interfaccia con mouse simulati, senza hardware
./run.sh --check            # verifica dipendenze e servizi, poi esce
./run.sh --install-deps     # installa le dipendenze mancanti (chiede Y/N)
./run.sh --yes              # installa tutto senza domande
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
                                                                    |- ratbag    (D-Bus verso ratbagd: mouse)
                                                                    |- openrgb   (CLI OpenRGB: RGB tastiere/cuffie)
                                                                    |- headset   (CLI HeadsetControl: cuffie USB)
                                                                    |- sysinput  (periferiche cablate e porte seriali:
                                                                    |             sola lettura, sempre presenti)
                                                                    |- hid       (laboratorio HID: nodi hidraw, descrittori,
                                                                    |             cattura e invio dei report)
                                                                    '- mock      (--mock: mouse, tastiera e cuffia simulati)
```

Ogni dispositivo ha un `kind` (`mouse`, `keyboard`, `headset`, `other`): la scheda
apre la pagina giusta (DPI, Illuminazione o Cuffie) in base a cosa il dispositivo sa
fare. `--mock` simula tutte e tre le pagine, utile per provare l'interfaccia senza
hardware.

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
Mint, Mobian, Arch, openSUSE), l'installer delle dipendenze (prompt Y/N, comandi per
distro, scelta dell'interprete), i backend OpenRGB e HeadsetControl (parsing e comandi,
con output reali dei due strumenti), il rilevamento di sistema (tastiere cablate unite
per VID/PID, esclusione di rumore e dispositivi virtuali, porte seriali), il laboratorio
HID (parsing dei descrittori con un descrittore di tastiera RGB, punteggio per scegliere
il nodo di configurazione, udev, invio e lettura dei report, flusso di cattura del
controller), l'archivio delle ultime impostazioni e il backend ratbag contro un finto
`ratbagd` su bus di sessione (`KOGITECHHUB_BUS=session`).

Per provare le pagine nuove senza hardware: `./run.sh --mock` (mouse, tastiera RGB e
cuffia simulati).

## Problemi comuni

- Banner "KogitechHub non riesce a parlare con libratbag": `sudo systemctl enable --now ratbagd`.
- Un mouse appare in sola lettura: libratbag non lo supporta (`ratbagctl list` non lo elenca).
- Una **tastiera cablata** compare in sola lettura con la nota "OpenRGB non la riconosce":
  è normale per i modelli fuori dalla lista OpenRGB (`openrgb -l` per verificare). In quel caso
  usa **Apri laboratorio HID**: elenca i nodi hidraw del dispositivo (spesso quello di
  configurazione dichiara report `feature` su pagina `0xFF00`), permette di leggere lo stato
  corrente e di inviare report, cioè di ricostruire il protocollo dell'RGB senza avere il
  software del produttore.
- Nel laboratorio HID un nodo appare **bloccato**: premi "Abilita accesso" (installa una regola
  udev `uaccess` per quel VID/PID, chiede la password).
- `scripts/hid_sniff.py capture` o "Avvia" non mostrano niente: il dispositivo parla solo quando
  cambia qualcosa. Cambia effetto/luminosità mentre la cattura è attiva, oppure prova a leggere i
  report feature (che mostrano lo stato anche da fermo).
- Se una periferica **non compare affatto**, controlla `/proc/bus/input/devices`: deve avere
  `Bus=0003` (USB) o `Bus=0005` (Bluetooth) e un handler `mouseN`/`kbd`. I dispositivi virtuali
  (`/devices/virtual/...`, passthrough) e i ricevitori audio/microfono vengono esclusi apposta.
- Una cuffia non compare in KogitechHub: HeadsetControl non la supporta (`headsetcontrol -b`
  per verificare) oppure il pacchetto non è installato (lo propone `./run.sh`).
- Colori e luminosità RGB non sono leggibili: OpenRGB espone solo la modalità attiva, quindi
  l'app mostra gli ultimi valori scritti da lei.
- I mouse wireless dietro un ricevitore (Unifying/Nano) non sono ancora configurabili.
- I valori DPI che il mouse accetta sono quelli che dichiara il dispositivo: digitandone
  uno diverso dal set supportato, l'app lo converte nel valore supportato più vicino e lo
  segnala (KogitechHub mostra sempre il valore che il dispositivo ha effettivamente memorizzato).

## Crediti

Ispirato a Logitech G HUB; basato su libratbag/ratbagd e Qt 6 (PySide6).
Tutti i grafica e il testo sono originali di questo progetto.
