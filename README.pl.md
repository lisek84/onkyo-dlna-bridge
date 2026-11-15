# onkyo-dlna-bridge

[English](README.md) | **Polski**

[![image](https://github.com/lisek84/onkyo-dlna-bridge/actions/workflows/image.yml/badge.svg)](https://github.com/lisek84/onkyo-dlna-bridge/actions/workflows/image.yml)

**Spotify na sprzęcie audio, który nie ma własnego (działającego) Spotify** – na dowolnym
**odtwarzaczu DLNA/UPnP (renderer)**: amplitunerach, odtwarzaczach sieciowych, telewizorach, Kodi… Projekt
powstał dla starszych **amplitunerów sieciowych Onkyo** (z lat ok. 2010–2013, np. TX-NR609), których
wbudowane Spotify przestało działać, gdy Spotify wycofało starą bibliotekę libspotify – i z urządzeniami
Onkyo / Integra współpracuje najpełniej.

Mały kontener na NAS-ie, Raspberry Pi albo dowolnym komputerze z Linuksem uruchamia **Spotify Soloist** –
oficjalnego klienta od samego Spotify – i przesyła dźwięk do odtwarzacza DLNA urządzenia. W aplikacji
Spotify wybierasz urządzenie z listy i muzyka gra właśnie tam, z tytułem, wykonawcą, albumem i okładką
przesyłanymi przy każdym utworze.

Na amplitunerach **Onkyo / Integra** (sterowanie eISCP) dodatkowo włącza amplituner i przełącza wejście,
pokazuje utwór na wyświetlaczu i okładkę na telewizorze, obsługuje przyciski **Stop** / **NET** / wyłączania
na pilocie, a opcjonalnie synchronizuje głośność, przywraca poprzednie wejście i wyłącza amplituner. Na
innych urządzeniach działa odtwarzanie i zwykle informacje o utworze – zob.
**[docs/compatibility.md](docs/compatibility.md)** (po angielsku).

> To niezależny projekt hobbystyczny. **Nie jest powiązany ze Spotify, wspierany ani certyfikowany przez
> Spotify** (amplituner nie staje się certyfikowanym urządzeniem „Spotify Connect”) **ani przez Onkyo**.
> Wyłącznie do prywatnego, niekomercyjnego użytku.

## Jak to wygląda

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/images/receiver-display.jpg" alt="Wyświetlacz Onkyo TX-NR609 z tytułem i wykonawcą utworu ze Spotify" width="100%"><br>
      <sub><b>Wyświetlacz amplitunera</b> – tytuł i wykonawca ze Spotify, wejście NET przełączone automatycznie</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/images/tv-osd-cover.jpg" alt="Telewizor z ekranem DLNA amplitunera: okładka, tytuł, wykonawca i album" width="75%"><br>
      <sub><b>Telewizor przez HDMI (menu ekranowe amplitunera)</b> – okładka, tytuł, czas, wykonawca i album</sub>
    </td>
  </tr>
</table>

Wybierasz amplituner w aplikacji Spotify na telefonie – a on sam się włącza, przełącza na wejście NET
i gra, pokazując, co leci, na swoim wyświetlaczu i na telewizorze. Cała reszta (playlisty, wyszukiwanie,
przełączanie utworów) zostaje w aplikacji Spotify, której i tak używasz.

Bez modyfikowania firmware'u i bez żadnych „hacków” na amplitunerze: wykorzystywane są wyłącznie jego
oficjalne interfejsy sieciowe (UPnP/DLNA oraz protokół sterowania Onkyo eISCP).

## Dlaczego ten projekt powstał

*Osobista notka autora.*

Mój Onkyo TX-NR609 to w pełni sprawny, dobry amplituner. Miał wbudowane Spotify – do czasu, aż Spotify
wycofało swoją starą bibliotekę libspotify, a Onkyo po prostu przestało interesować się urządzeniami tej
generacji. Żadnej aktualizacji, żadnego zamiennika, nic: pozycja „Spotify” w menu po cichu przestała działać
i została tam, martwa. Tysiące dobrych urządzeń z dnia na dzień straciło funkcję przez decyzję podjętą gdzieś
indziej – i to zdenerwowało mnie na tyle, żeby coś z tym zrobić.

Chciałem rozwiązania, które szanuje zarówno urządzenie, jak i zasady Spotify, dlatego projekt celowo
korzysta wyłącznie z oficjalnych elementów:

- Używa **Spotify Soloist – oficjalnego klienta od samego Spotify** – z Twoim własnym kluczem API
  dewelopera. Żadnego klienta Spotify odtworzonego metodą inżynierii wstecznej, żadnego obchodzenia czegokolwiek.
- Soloist **nie jest redystrybuowany** – każda instalacja pobiera go z oficjalnego serwera (CDN) Spotify,
  tak jak prosi o to Spotify.
- Dźwięk trafia **wyłącznie do Twojego amplitunera** w domowej sieci (domyślnie inne urządzenia dostają
  odmowę) i **nigdy nie jest nagrywany ani zapisywany**.
- Amplituner jest sterowany wyłącznie przez **interfejsy, które oficjalnie udostępnia** w sieci (odtwarzacz
  DLNA i udokumentowany protokół eISCP Onkyo). Jego oprogramowanie nie jest w żaden sposób zmieniane.

Jeśli masz stary amplituner, którego funkcje streamingowe zostały porzucone w ten sam sposób – mam nadzieję,
że to da mu drugie życie.

## Jak to działa, w skrócie

```
 aplikacja Spotify ──Spotify Connect──►  Soloist ─► PulseAudio ─► swyh-rs ─► proxy HTTP ──DLNA/HTTP──► amplituner
 (telefon/PC)                            └────────────── kontener (sieć hosta) ─────────┘    ▲
                                          sterowanie amplitunerem: UPnP AVTransport + eISCP (TCP 60128) ┘
```

Szczegóły (po angielsku): [docs/how-it-works.md](docs/how-it-works.md). Dokumentacja techniczna amplitunera dla deweloperów: [docs/receiver-internals.md](docs/receiver-internals.md).

## Funkcje

**Z dowolnym odtwarzaczem DLNA / UPnP**

- Widoczny na liście urządzeń w aplikacji Spotify dzięki oficjalnemu klientowi **Spotify Soloist** (bez klientów z inżynierii wstecznej)
- Bezstratny strumień **LPCM 44,1 kHz / 16 bit**, udostępniany tylko skonfigurowanemu odtwarzaczowi
- **Tytuł / wykonawca / album** i **okładka** przesyłane przy każdej zmianie utworu (podcasty: nazwa podcastu)
- Soloist jest pobierany z CDN Spotify przy starcie i **aktualizowany automatycznie** (buildy wygasają po 90 dniach)

**Dodatki na amplitunerach Onkyo / Integra (eISCP)**

- **Włącza amplituner** i przełącza go na NET → DLNA, gdy zaczynasz odtwarzanie; utwór na wyświetlaczu,
  okładka na telewizorze (menu ekranowe amplitunera przez HDMI)
- Pilot: **Stop** pauzuje Spotify, **NET** wznawia (opcjonalnie: następny utwór w trakcie grania),
  **wyłączenie amplitunera** pauzuje Spotify (opcjonalnie: oddaje odtwarzanie telefonowi)
- Opcjonalnie: suwak głośności w Spotify ↔ głośność amplitunera, głośność startowa, powrót do poprzedniego
  wejścia, automatyczne przejście w standby
- Obchodzi problemy starego oprogramowania odtwarzacza DLNA (błąd UPnP 705 „Transport is locked”,
  sprawdzanie strumienia zapytaniami Range, metadane)

## Stan / przetestowany sprzęt

| Element | Testy |
|---|---|
| Amplituner | **Onkyo TX-NR609** (2011) |
| Host | **Synology DS718+** (x86_64, DSM 7.2, Container Manager) |
| Inny Linux x86_64 + Docker / Podman | powinien działać (ten sam obraz) |
| Raspberry Pi / ARM (`Dockerfile.arm`) | **nietestowane** – swyh-rs jest kompilowany ze źródeł |
| Windows (WSL2) | **eksperymentalnie / nietestowane** – zob. [docs/windows.md](docs/windows.md) |

Odtwarzacze DLNA innych marek oraz inne amplitunery Onkyo / Integra powinny działać – w pełni albo
częściowo, zob. [docs/compatibility.md](docs/compatibility.md) – ale nie były jeszcze testowane. Zgłoszenia (czy działa, czy nie) mile widziane w
[issues](https://github.com/lisek84/onkyo-dlna-bridge/issues).

## Wymagania

- Darmowy **klucz API Spotify Soloist**, utworzony z konta **Spotify Premium** (gdy już działa, odtwarzać na nim
  mogą użytkownicy Free i Premium) → zob. [Klucz API](#klucz-api-spotify-soloist) poniżej
- Komputer/NAS w **tej samej sieci LAN** co amplituner, z Dockerem lub Podmanem, **siecią hosta**
  (`network_mode: host`) i ok. 100 MB RAM (x86_64, arm64 lub armv7; obraz oparty o glibc, Debian trixie)
- Amplituner z włączoną siecią, stałym adresem IP i dwoma sprawdzonymi ustawieniami → [Przygotowanie amplitunera](#przygotowanie-amplitunera)
- **Zapora (firewall):** amplituner musi móc połączyć się z hostem na porcie **TCP 5901** (`STREAM_PORT`),
  a mDNS (UDP 5353) musi docierać do hosta → [Sieć i zapora](#sieć-i-zapora-firewall)

## Klucz API Spotify Soloist

Potrzebny jest **jeden osobisty klucz API**. Jest darmowy, ale konto Spotify, które go tworzy, musi mieć
**Spotify Premium** (później, gdy Soloist już działa, odtwarzać na nim mogą też użytkownicy kont Free).
**Nie** trzeba tworzyć żadnej „aplikacji” ani Client ID/Secret.

1. Wejdź na **<https://developer.spotify.com/>** i zaloguj się swoim kontem Spotify (Premium). Przy pierwszej
   wizycie zaakceptuj warunki Spotify for Developers.
2. Otwórz **Dashboard** → stronę **Spotify Soloist API Key**: **<https://developer.spotify.com/dashboard/soloist>**
3. Zapoznaj się z warunkami i zaakceptuj je, jeśli zostaniesz o to poproszony, a potem **wygeneruj klucz API**.
4. Wpisz klucz do `soloist.env`: `SOLOIST_API_KEY=twój_klucz`

**Klucz jest prywatny** i przypisany do Twojego konta – nie publikuj go, nie wklejaj do zgłoszeń ani logów
(`soloist.env` jest w `.gitignore`). Przy pierwszym wybraniu urządzenia w aplikacji Spotify Soloist loguje się
na konto, z którego je wybrano; logowanie jest zapisywane w `config/soloist-data/` i przetrwa restarty
i przebudowy obrazu. Więcej (po angielsku): [docs/spotify-developer-key.md](docs/spotify-developer-key.md).

## Przygotowanie amplitunera

1. **Sieć i stały IP:** podłącz amplituner do sieci (najlepiej kablem), sprawdź, że działa NET (np. radio
   internetowe), i nadaj mu **stały adres IP** – najprościej rezerwacją DHCP w routerze (po adresie MAC).
   Ten adres wpisz do `RENDERER_IP`.
2. Włącz **Network Standby** (Setup → Hardware/Network Setup – nazwa zależy od modelu). Bez tego amplituner
   w trybie czuwania jest niedostępny w sieci i nie da się go zdalnie włączyć.
3. W przeglądarce otwórz `http://<ip-amplitunera>/` → **Unit information**:
   - **DMR Max Volume (0-100)** – ustaw np. **60–70**. Przy wartości `0` głośność spada do zera przy każdym
     utworze – najczęstsza przyczyna „gra, ale nic nie słychać”.
   - **Auto Play** – **Yes**.
   - Kliknij **SAVE**.
4. Jeśli odtwarzacz DLNA amplitunera kiedyś całkowicie się zawiesi (brak odpowiedzi na porcie 8888), pomaga
   tylko odłączenie zasilania na ok. 30 s – tryb czuwania nie restartuje modułu sieciowego.

Więcej (po angielsku): [docs/receiver-setup.md](docs/receiver-setup.md).

## Sieć i zapora (firewall)

Kontener działa w **sieci hosta** (`network_mode: host`) – inaczej nie zadziała ani wykrywanie urządzenia
w Spotify (mDNS), ani połączenie amplitunera z hostem.

> **Najczęstszy błąd konfiguracji:** zapora na hoście po cichu blokuje połączenie **amplitunera** do
> **TCP 5901**. Amplituner odpowiada wtedy na każde polecenie odtwarzania błędem UPnP **705 „Transport is
> locked”** (to jego ogólny komunikat „nie mogę otworzyć strumienia”), nic nie gra, a w logu brakuje linii
> `[proxy] <ip-amplitunera> GET /stream.lpcm`. Test z własnego komputera niczego nie dowodzi – reguła musi
> wpuszczać **adres IP amplitunera**.

| Kierunek | Protokół / port | Po co |
|---|---|---|
| **amplituner → host** | **TCP 5901** (`STREAM_PORT`) | amplituner pobiera strumień audio – **otwórz w zaporze** |
| telefon/PC → host | UDP 5353 (mDNS) + dynamiczny port TCP Soloist | aplikacja Spotify wykrywa urządzenie i łączy się z nim |
| host → amplituner | TCP 8888 i UDP 1900 (UPnP/SSDP), TCP 60128 (eISCP) | sterowanie odtwarzaniem, włączanie, wejście |
| host → internet | HTTPS | streaming Spotify i pobieranie Soloist |

**Synology DSM** (jeśli zapora DSM jest włączona): Panel sterowania → Zabezpieczenia → Zapora → Edytuj
reguły → Utwórz: Porty **Niestandardowe** → **TCP 5901**, Źródłowy adres IP → **adres amplitunera** (albo
cała podsieć LAN), Działanie → **Zezwól**; przesuń regułę nad reguły „Odmów”. Wpuść też mDNS (UDP 5353) z LAN.

**ufw (Ubuntu, Raspberry Pi OS):**
```bash
sudo ufw allow from 192.168.1.50 to any port 5901 proto tcp     # IP amplitunera
sudo ufw allow from 192.168.1.0/24 to any port 5353 proto udp   # mDNS z LAN
```
Przepisy dla firewalld i więcej szczegółów (po angielsku): [docs/networking.md](docs/networking.md).

## Szybki start (Docker / Podman na Linuksie)

```bash
git clone https://github.com/lisek84/onkyo-dlna-bridge.git
cd onkyo-dlna-bridge
cp soloist.env.example soloist.env
nano soloist.env               # SOLOIST_API_KEY, RENDERER_IP, DEVICE_NAME, PUID/PGID
docker compose up -d --build   # Raspberry Pi: najpierw ustaw w compose.yaml dockerfile: Dockerfile.arm
docker compose logs -f
```

Otwórz Spotify na telefonie → **Urządzenia** → wybierz swoje `DEVICE_NAME` → odtwarzaj.
Przy pierwszym połączeniu Soloist loguje się na Twoje konto; później łączy się już sam.

**Gotowy obraz (opcjonalnie):** workflow GitHub Actions publikuje obraz wieloarchitekturowy (amd64, arm64)
w `ghcr.io/lisek84/onkyo-dlna-bridge`. Aby go użyć zamiast budować lokalnie, zastąp blok `build:`
w `compose.yaml` linią `image: ghcr.io/lisek84/onkyo-dlna-bridge:latest`.

### Synology DSM (Container Manager)

1. Zainstaluj **Container Manager** z Centrum pakietów.
2. Utwórz folder `/volume1/docker/onkyo-dlna-bridge` i skopiuj do niego: `deploy/synology/compose.yaml`
   → `compose.yaml`, cały folder `image/` → `image/`, `soloist.env.example` → `soloist.env`.
3. Uzupełnij `soloist.env`: klucz API, `RENDERER_IP`, `DEVICE_NAME`, `PUID`/`PGID` (zwykle `1026`/`100`,
   sprawdzisz przez SSH poleceniem `id`) i zalecane na Synology `HOST_IP` (adres NAS w LAN).
4. Jeśli zapora DSM jest włączona – reguła dla **TCP 5901 z adresu amplitunera** (patrz wyżej).
5. Container Manager → **Projekt** → **Utwórz** → ścieżka: folder z punktu 2 → „użyj istniejącego
   compose.yaml” → Gotowe. Obraz się zbuduje (kilka minut) i kontener wystartuje.
6. Log: Container Manager → Kontener → Log, albo plik `config/container.log`.

Pełna instrukcja (po angielsku): [docs/synology.md](docs/synology.md).
Linux, Raspberry Pi, Podman / Quadlet: [docs/linux.md](docs/linux.md). Windows (WSL2): [docs/windows.md](docs/windows.md).

## Konfiguracja

Wszystkie ustawienia są w `soloist.env` (pełne komentarze w [soloist.env.example](soloist.env.example)).

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `SOLOIST_API_KEY` | – (wymagane) | Twój klucz API Spotify Soloist |
| `RENDERER_IP` | – (wymagane) | Adres IP amplitunera |
| `DEVICE_NAME` | `Onkyo Receiver` | Nazwa w aplikacji Spotify |
| `HOST_IP` | auto | Adres IP hosta w LAN (ustaw, jeśli host ma kilka sieci) |
| `PUID` / `PGID` | `1000` / `1000` | Właściciel `./config` (Synology: zwykle `1026` / `100`) |
| `STREAM_PORT` | `5901` | Port TCP, z którego amplituner pobiera dźwięk – **otwórz w zaporze** |
| `STREAM_ALLOW` | `renderer` | Kto może pobrać strumień: `renderer` (tylko `RENDERER_IP`), lista adresów/podsieci albo pusto (każdy w LAN) |
| `SWYH_PORT` | `5911` | Wewnętrzny port przechwytywania dźwięku (tylko localhost) |
| `INITIAL_VOLUME` | `70` | Początkowa (cyfrowa) głośność Spotify |
| `META_UPDATE` | `yes` | Tytuł/wykonawca na wyświetlaczu (2–4 s przerwy na początku utworu); `no` = bez przerw, stały `PLAY_TITLE` |
| `PLAY_TITLE` | `Spotify` | Tekst na wyświetlaczu, gdy nie są wysyłane metadane |
| `COVER_ART` | `yes` | Wysyłaj okładkę albumu (widoczna na telewizorze przez menu ekranowe amplitunera) |
| `COVER_SIZE` | `default` | Rozmiar okładki: `default` (300 px), `large` (640 px), `small` (64 px) |
| `ONKYO_EISCP` | `yes` | Używaj protokołu Onkyo eISCP; `no` dla odtwarzaczy innych niż Onkyo |
| `AUTO_POWER_ON` | `yes` | Włączaj amplituner, gdy zaczyna się odtwarzanie |
| `REMOTE_CONTROL` | `yes` | Pilot: Stop → pauza, NET → wznowienie, wyłączenie → pauza |
| `NET_RESUME_SECONDS` | `120` | Jak długo po Stop przycisk NET wznawia odtwarzanie (NET otwiera też menu NET) |
| `POWER_OFF_ACTION` | `pause` | Wyłączenie amplitunera: `pause` = pauza w Spotify, `release` = pauza i rozłączenie (aplikacja wraca na telefon) |
| `NET_NEXT` | `no` | `yes` = NET w trakcie odtwarzania przełącza na następny utwór (menu NET: najpierw Stop) |
| `VOLUME_SYNC` | `no` | Suwak głośności w Spotify ↔ głośność amplitunera, w obie strony |
| `VOLUME_MAX` | `50` | Głośność amplitunera odpowiadająca 100 % w Spotify (twardy limit) |
| `POWER_ON_VOLUME` | *(puste)* | Głośność ustawiana tylko wtedy, gdy to kontener włącza amplituner. **Puste = amplituner włącza się z taką głośnością, jaką zawsze miał** |
| `RESTORE_INPUT` | `no` | Powrót do poprzedniego wejścia (np. TV), gdy Spotify skończy |
| `AUTO_POWER_OFF_MINUTES` | `0` | Standby po N minutach bez Spotify, jeśli to kontener włączył amplituner |
| `IDLE_STOP_SECONDS` | `300` | Zatrzymaj strumień po tylu sekundach pauzy |
| `LOG_TO_FILE` | `yes` | Zapisuj log także do `config/container.log` |

**Opcje głośności działają niezależnie od siebie:**

| Chcesz | Ustawienia |
|---|---|
| Nie ruszać głośności amplitunera; suwak w Spotify zmienia tylko poziom strumienia (domyślnie) | `VOLUME_SYNC=no`, `POWER_ON_VOLUME=` |
| Suwak w Spotify steruje amplitunerem, bez głośności startowej | `VOLUME_SYNC=yes`, `POWER_ON_VOLUME=` |
| Tylko stała głośność startowa | `VOLUME_SYNC=no`, `POWER_ON_VOLUME=35` |
| Oba | `VOLUME_SYNC=yes`, `POWER_ON_VOLUME=35` |

Gdy `POWER_ON_VOLUME` jest puste (albo linii nie ma), amplituner włącza się z taką głośnością, jaką miał ostatnio –
kontener jej nie zmienia. Włączonego już amplitunera kontener też nigdy nie rusza. Przy `VOLUME_SYNC=yes` suwak
w Spotify na starcie odtwarzania ustawia się według aktualnej głośności amplitunera – przesuwa się tylko suwak,
amplituner zachowuje swoją głośność.

## Jak z tego korzystać

| Robisz | Co się dzieje |
|---|---|
| Wybierasz urządzenie w Spotify i włączasz odtwarzanie | Amplituner włącza się, przechodzi na NET → DLNA i gra (≈ 8–15 s) |
| Zmieniasz utwór w aplikacji Spotify | Gra dalej; wyświetlacz pokazuje nowy tytuł i okładkę (`META_UPDATE=yes`) |
| **Stop** na pilocie amplitunera | Spotify się pauzuje |
| **NET** na pilocie do 2 min po Stop | Spotify wznawia odtwarzanie (≈ 8 s do dźwięku) |
| **NET** w trakcie odtwarzania (przy `NET_NEXT=yes`) | następny utwór (≈ 3 s) |
| Wyłączasz amplituner | Spotify się pauzuje; amplituner **nie** zostanie z powrotem włączony |
| Głośność na pilocie / w Spotify | Pilot = głośność amplitunera; suwak w Spotify = głośność strumienia, albo głośność amplitunera przy `VOLUME_SYNC=yes` |

**Niemożliwe:** Play/Pause/Next/Previous/FF na pilocie amplitunera. W trybie odtwarzacza DLNA te amplitunery
obsługują te przyciski wewnętrznie i nie zgłaszają ich w sieci (sprawdzone przez eISCP i UPnP). Do
przełączania utworów używaj aplikacji Spotify.

## Rozwiązywanie problemów (najczęstsze)

| Objaw | Przyczyna / rozwiązanie |
|---|---|
| Urządzenie nie pojawia się w Spotify | Brak `network_mode: host`; telefon w innej sieci/VLAN lub sieci gości; zablokowany mDNS (UDP 5353) |
| W aplikacji „gra”, amplituner nic nie robi, w logu `Play … 705` i brak linii `[proxy] <ip-amplitunera> GET` | **Zapora blokuje amplitunerowi TCP 5901** albo zły `HOST_IP` |
| Linie `[proxy] … GET` są, a mimo to 705 | Odłącz amplituner od zasilania na ~30 s |
| Gra, ale nic nie słychać | **DMR Max Volume = 0** na stronie amplitunera albo bardzo niska głośność w Spotify |
| Tytuł na wyświetlaczu amplitunera odjeżdża i znika na ~2 minuty | Ograniczenie firmware amplitunera w trybie DLNA (oficjalna aplikacja Onkyo ma to samo): dopełnia tekst do 64 znaków i przewija też puste miejsce. Nie da się tego naprawić bez zmiany firmware; telewizor pokazuje wszystko poprawnie |
| Krótkie przerwy na początku każdego utworu | Normalne przy `META_UPDATE=yes`; ustaw `no`, jeśli wolisz bez przerw |
| Po ~3 miesiącach przestało działać | Build Soloist wygasł; kontener sam pobiera nowy po restarcie (`restart: unless-stopped`, dostęp do internetu) |

Więcej (po angielsku): [docs/troubleshooting.md](docs/troubleshooting.md).

## Dokumentacja (po angielsku)

- [Zgodność z innymi amplitunerami i odtwarzaczami DLNA](docs/compatibility.md)
- [Jak to działa](docs/how-it-works.md) – architektura i obchodzone problemy starego odtwarzacza DLNA
- [Dlaczego Spotify Soloist (a nie librespot/spotifyd/…)](docs/why-soloist.md)
- [Klucz API Spotify Soloist](docs/spotify-developer-key.md)
- [Przygotowanie amplitunera](docs/receiver-setup.md)
- [Sieć i zapora](docs/networking.md)
- [Rozwiązywanie problemów](docs/troubleshooting.md)

## Kwestie prawne

- Ten projekt **nie jest powiązany ze Spotify ani z Onkyo, nie jest przez nie wspierany, sponsorowany ani
  certyfikowany**. „Spotify”, „Spotify Connect”, „Spotify Soloist” i „Onkyo” są znakami towarowymi ich
  właścicieli i są tu używane wyłącznie do opisania zgodności. Nie używamy logo ani elementów marki Spotify.
- **Wyłącznie do prywatnego, niekomercyjnego użytku**, zgodnie z warunkami Spotify dla deweloperów. Projekt
  nie nagrywa, nie zapisuje i nie udostępnia żadnych treści Spotify: dźwięk jest przesyłany na żywo, tylko do
  Twojego amplitunera (domyślnie `STREAM_ALLOW=renderer`).
- **Spotify Soloist nie jest tu rozpowszechniany.** Kontener pobiera go z oficjalnego CDN Spotify przy
  uruchomieniu; jego używanie podlega warunkom Spotify akceptowanym przy generowaniu klucza API
  (zob. [dokumentację Spotify Soloist](https://developer.spotify.com/documentation/soloist)).
  Twój klucz API jest osobisty – nie udostępniaj go.
- **Co zawiera obraz kontenera:** skrypty tego projektu, pakiety Debiana oraz program
  [swyh-rs](https://github.com/dheijl/swyh-rs) (MIT © dheijl – jego licencja jest dołączona w obrazie:
  `/usr/share/doc/swyh-rs/LICENSE`). Obraz **nie** zawiera Spotify Soloist.
- Kod w tym repozytorium jest udostępniony na [licencji MIT](LICENSE) © Lisek ([lisek84](https://github.com/lisek84)).
