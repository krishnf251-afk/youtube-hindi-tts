from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8501")
        time.sleep(2)  # Wait for Streamlit to load

        print("Page title:", page.title())

        # We need a small video for testing
        test_video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

        # Fill in the URL
        page.fill("input[aria-label='YouTube Video URL']", test_video_url)

        # Click the "Process Video" button
        page.click("button:has-text('Process Video')")

        print("Clicked process button, waiting for processing to complete...")

        # Wait for the success message (timeout after 60s)
        try:
            page.wait_for_selector("text=Processing complete!", timeout=60000)
            print("Successfully found 'Processing complete!' message.")

            # check if audio is there
            audio_element = page.query_selector("audio")
            if audio_element:
                print("Audio element found.")
            else:
                print("No audio element found.")
        except Exception as e:
            print(f"Error waiting for success: {e}")

        browser.close()

if __name__ == "__main__":
    run()
