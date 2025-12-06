# WinCord – Sync Discord avatar to Windows
WinCord is a Python application that automatically updates your Windows account picture using your Discord avatar. It runs in the system tray, monitors your avatar on Discord, and updates your Windows avatar silently using PsExec.

## Features
- Automatically updates your Windows avatar from Discord.
- Supports both PNG and GIF avatars.
- Runs in the background via system tray.
- Saves avatar images locally in the `avatar` folder.
- Logs activity in the `logs` folder.
- Can be added to Windows startup.
- Uses OAuth2 to securely authenticate with Discord.

## Installation

1. **Download ZIP**  
   Download `WinCord.zip` from the [Releases](https://github.com/Enmn/WinCord/releases) page.

2. **Extract ZIP**  
   Extract the ZIP file to any folder on your computer.

3. **Run the EXE**  
   Open the extracted folder and run `WinCord.exe`.  
   On first launch, the GUI window will appear.

4. **Startup (Run on Windows Startup)**  
   - WinCord automatically adds itself to the Startup folder.  
   - On system boot, the program runs in the background (Tray Icon) without showing the GUI.  
   - You can open the GUI manually via the tray icon (Right Click → Open WinCord).


## Getting Discord Client ID and Secret

WinCord needs your **Discord Client ID** and **Client Secret** to connect to your account and fetch your avatar.

1. **Go to the Discord Developer Portal:**  
   [https://discord.com/developers/applications](https://discord.com/developers/applications)  
   Log in with your Discord account if prompted.

2. **Create a New Application:**  
   - Click **“New Application”**.  
   - Enter a name (e.g., `WinCordApp`) and click **Create**.

3. **Get Client ID and Secret:**  
   - Go to **OAuth2** → **General**.  
   - Copy the **Client ID**.  
   - Click **“Click to Reveal”** to see the **Client Secret** and copy it.  
   > Keep your Client Secret private!

4. **Set Redirect URI**
   - Go to **OAuth2** → **Redirects**.
   - Add http://localhost:8000/callback and save.
   > This is required so WinCord can receive the authorization code from Discord.

## Usage
1. Open the application manually or let it run on startup.
2. Paste your Client ID and Client Secret into the WinCord GUI and click **Save Config**.  
3. Click **Connect** to authorize your Discord account.
4. Once authorized, the program will monitor your Discord avatar and update Windows automatically.
5. Stop or start watching using the buttons in the GUI or via the system tray menu.

## Notes
- Ensure PsExec.exe is present in the `tools` folder.
- The application will add itself to startup silently, running in tray mode if started automatically.
- To open the GUI, right-click the tray icon.
- Logs are saved in `logs/app.log`.
- Avatars are saved in `avatar/` folder next to EXE.

## Support
For issues or feature requests, please open an issue in the GitHub repository.

## License
This project is licensed under the MIT License - see the LICENSE file for details.