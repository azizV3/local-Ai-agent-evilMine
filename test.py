import asyncio
import json
import websockets


async def handle_minecraft_client(websocket):
    print("🤖 Minecraft agent connected via Minescript!")

    try:
        async for message in websocket:
            data = json.loads(message)
            pos = data.get("pos", [0, 0, 0])
            nearby_players = data.get("nearby_players", [])

            print(
                f"📥 Agent Pos: {pos} | Nearby Players Detected: {len(nearby_players)}"
            )

            # Default response
            command_response = {"action": "idle"}

            # Decision Logic: If nearby players exist, pick the closest one
            if nearby_players:
                closest_player = min(nearby_players, key=lambda p: p["distance"])
                print(
                    f"🎯 Target selected: {closest_player['name']} at {closest_player['pos']} ({closest_player['distance']}m away)"
                )

                command_response = {
                    "action": "go_to_player",
                    "target_name": closest_player["name"],
                    "target_pos": closest_player["pos"],
                }

            await websocket.send(json.dumps(command_response))

    except websockets.exceptions.ConnectionClosed:
        print("❌ Minecraft agent disconnected.")


async def main():
    async with websockets.serve(handle_minecraft_client, "127.0.0.1", 8765):
        print("🚀 Agent WebSocket Server running on ws://127.0.0.1:8765...")
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())