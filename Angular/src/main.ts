import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * Polls the backend health endpoint until it responds with "ready": true.
 * Uses the native fetch API so that we don’t need Angular's HttpClient (which
 * would require bootstrapping before use).
 */
async function waitForBackendReady(): Promise<void> {
  const healthUrl = 'http://localhost:5000/api/health';
  while (true) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        const data = await response.json();
        console.log('Backend health response:', data);
        if (data.ready) {
          console.log('Backend is ready.');
          break;
        }
      }
    } catch (err) {
      console.warn('Backend not ready yet:', err);
    }

    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

// Main function: first wait for backend, then bootstrap the Angular app.
async function main() {
  await waitForBackendReady();
  bootstrapApplication(AppComponent, appConfig)
    .catch(err => console.error(err));
}

// Call main to start the app.
main();
