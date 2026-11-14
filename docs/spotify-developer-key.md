# Getting a Spotify Soloist API key

You need **one personal API key**. It is free, but the Spotify account that creates it must have
**Spotify Premium**. You do **not** need to create a Spotify "app" or a client ID/secret for Soloist.

## Steps

1. Go to **<https://developer.spotify.com/>** and log in with your Spotify (Premium) account.
   If this is your first visit, accept the Spotify for Developers terms when asked.
2. Open the **Dashboard** and go to the **Spotify Soloist API Key** page:
   **<https://developer.spotify.com/dashboard/soloist>**
3. Review and accept the Spotify terms if prompted, then **generate an API key** on that page.
4. Copy the key into `soloist.env`:

   ```ini
   SOLOIST_API_KEY=your_key_here
   ```

## Good to know

- **Keep the key private.** It is tied to your account. Do not commit `soloist.env` (it is in
  `.gitignore`), do not post it in issues or logs. If it leaks, generate a new one on the same page.
- One key is enough for your household's device(s); every person running their own instance should
  create their own key.
- On the first start the device appears in the Spotify app (Devices list). Selecting it logs Soloist into
  the Spotify account that selected it (Spotify Connect pairing). The login is stored in
  `config/soloist-data/` and survives container restarts and image rebuilds.
- To "log out" the device, stop the container and delete `config/soloist-data/`.

Official documentation:
[Spotify Soloist](https://developer.spotify.com/documentation/soloist) ·
[Getting started](https://developer.spotify.com/documentation/soloist/tutorials/getting-started)
