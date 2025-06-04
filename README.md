# Unity Game Project

This Unity game allows players to control a ball, navigate levels, and achieve high scores. It features a scoring system and online leaderboards.

**Core Gameplay Mechanics:**
*   **Player Control:** Control the ball using on-screen joysticks or accelerometer input (on mobile devices).
*   **Scoring:** Earn points by reaching goals or performing specific actions within the game.
*   **Ranking System:** Submit scores to a server and view your rank on an online leaderboard.

## How to Build and Run

This is a Unity project.

1.  Clone this repository.
2.  Open the project using Unity Hub or the Unity Editor. It is expected to work with recent versions of Unity.
3.  All necessary external assets and plugins are included in the repository (see "External Assets and Plugins" section below).
4.  Open the `title` scene from the `Assets/Scenes/` directory.
5.  Click the "Play" button in the Unity Editor to run the game.

## Project Structure

*   `Assets/Scenes/`: Contains game scenes, such as `title.unity` (main menu) and `level1.unity` (game level).
*   `Assets/Scripts/`: Houses C# scripts for game logic. Key scripts include `Player.cs` (player controls), `Goal.cs` (level completion), and `RankingController.cs` (high score management).
*   `Assets/Prefabs/`: Stores pre-configured game objects (Prefabs) like player characters, enemies, or UI elements.
*   `Assets/Extensions/`: Directory for third-party Unity extensions.
*   `Assets/Plugins/`: Directory for native plugins.
*   `php_script/`: Contains PHP scripts (`addscore.php`, `display.php`) for the server-side leaderboard.

## External Assets and Plugins

This project utilizes the following external assets and plugins, which are included in the repository:

*   **CNControls:** Located in `Assets/CNControls/`. Used for on-screen joysticks and touchpads.
*   **MobileNativePopUps:** Located in `Assets/Extensions/MobileNativePopUps/`. Used for displaying native dialog pop-ups on mobile devices.
*   **SimpleNotificationForAndroid:** Located in `Assets/SimpleNotificationForAndroid/`. Used for creating local notifications on Android devices.

## Server-Side Components

The game includes a server-side component for managing online leaderboards, located in the `php_script/` directory.

*   **`addscore.php`:** This script is responsible for receiving scores submitted by the game client and storing them, likely in a MySQL database.
*   **`display.php`:** This script retrieves the stored scores from the database and returns them to the game client to display the leaderboard.

**Requirements:**
*   A web server with PHP support.
*   A MySQL database to store the scores.

**Configuration:**
The connection details for these scripts (such as the URLs and a secret key for hashing) are expected to be configured within the `Assets/Scripts/BBBWWW.cs` file in the Unity project. You will need to modify the `secretKey`, `addScoreURL`, and `highscoreURL` constants in this file to point to your server setup.
