import asyncio
import websockets
import sys

async def test_connection(uri):
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Successfully connected to {uri}")
            
            # Send a ping
            await websocket.send('{"type": "ping"}')
            print("Sent ping")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

async def main():
    base_url = "ws://localhost:3001"
    
    # Test coordinator endpoint
    coordinator_url = f"{base_url}/ws/coordinator"
    success1 = await test_connection(coordinator_url)
    
    # Test workflow endpoint
    workflow_url = f"{base_url}/ws/workflow/test_id"
    success2 = await test_connection(workflow_url)
    
    if success1 and success2:
        print("\n✅ All WebSocket tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some WebSocket tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
