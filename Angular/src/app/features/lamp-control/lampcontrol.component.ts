import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-lamp-control',
  templateUrl: './lamp-control.component.html',
  styleUrls: ['./lamp-control.component.css']
})
export class LampControlComponent implements OnInit, OnDestroy {
  private readonly BASE_URL = 'http://localhost:5000/api';
  currentLampStateImage: string = 'assets/images/lamp_off.png';
  currentPSUStateImage: string = 'assets/svg/lamp/PSU_off.svg';
  lampStatePolling: Subscription | undefined;
  psuStatePolling: Subscription | undefined;
  settings: any;
  currentLampState: number = -1; // Track the current lamp state
  currentPSUState: boolean = false; // Track the current PSU state
  isLampControllerConnected: boolean = true; // Track if the lamp controller is connected
  isPSUConnected: boolean = true; // Track if the PSU is connected

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    this.loadSettings();
    this.updateLampState();
    this.pollPSUState();
    this.checkConnections();
  }

  ngOnDestroy(): void {
    this.lampStatePolling?.unsubscribe();
    this.psuStatePolling?.unsubscribe();
  }

  loadSettings(): void {
    this.http.get('assets/settings.json').subscribe(
      (settings: any) => {
        this.settings = settings;
      },
      (error) => {
        console.error('Failed to load settings', error);
      }
    );
  }

  getChannelSettings(channel: number): any {
    if (this.settings && this.settings.channels) {
      return this.settings.channels.find((ch: any) => ch.channel === channel);
    }
    return null;
  }

  toggleLamp(channel: number): void {
    if (!this.isLampControllerConnected) return;

    const channelSettings = this.getChannelSettings(channel);
    if (!channelSettings) {
      console.error(`Settings for channel ${channel} not found`);
      return;
    }

    const payload = {
      channel: channel,
      on_time_ms: channelSettings.on_time_ms
    };

    this.http.post(`${this.BASE_URL}/toggle-lamp`, payload).subscribe(
      () => {
        this.pollLampState();
      },
      (error) => {
        console.error(`Failed to toggle channel ${channel}`, error);
      }
    );
  }

  togglePSU(): void {
    if (!this.isPSUConnected) return;

    const newState = !this.currentPSUState;
    this.http.post(`${this.BASE_URL}/toggle-psu`, { state: newState }).subscribe(
      () => {
        this.currentPSUState = newState;
        this.updatePSUImage();
      },
      (error) => {
        console.error('Failed to toggle PSU state', error);
      }
    );
  }

  pollLampState(): void {
    if (this.lampStatePolling) {
      this.lampStatePolling.unsubscribe();
    }

    this.lampStatePolling = interval(500).subscribe(() => {
      this.updateLampState();
    });
  }

  pollPSUState(): void {
    if (this.psuStatePolling) {
      this.psuStatePolling.unsubscribe();
    }

    this.psuStatePolling = interval(2000).subscribe(() => {
      this.updatePSUState();
    });
  }

  checkConnections(): void {
    this.http.get<{ lampControllerConnected: boolean, psuConnected: boolean }>(`${this.BASE_URL}/check-connections`).subscribe(
      (response) => {
        this.isLampControllerConnected = response.lampControllerConnected;
        this.isPSUConnected = response.psuConnected;

        if (!this.isPSUConnected) {
          this.psuStatePolling?.unsubscribe();
        }
      },
      (error) => {
        console.error('Failed to check connections', error);
        this.isLampControllerConnected = false;
        this.isPSUConnected = false;
        this.psuStatePolling?.unsubscribe();
      }
    );
  }

  updateLampState(): void {
    if (!this.isLampControllerConnected) {
      this.currentLampState = -1;
      this.setLampStateImage(-1);
      return;
    }

    this.http.get<number>(`${this.BASE_URL}/get-lamp-state`).subscribe(
      (state) => {
        this.currentLampState = state;
        this.setLampStateImage(state);
        if (state === -1) {
          this.lampStatePolling?.unsubscribe();
        }
      },
      (error) => {
        console.error('Failed to get lamp state', error);
        this.currentLampState = -1; // Default to lamp off in case of error
        this.setLampStateImage(-1);
      }
    );
  }

  updatePSUState(): void {
    if (!this.isPSUConnected) {
      this.currentPSUState = false;
      this.updatePSUImage();
      return;
    }

    this.http.get<{ state: boolean }>(`${this.BASE_URL}/get-psu-state`).subscribe(
      (response) => {
        this.currentPSUState = response.state;
        this.updatePSUImage();
      },
      (error) => {
        console.error('Failed to get PSU state', error);
      }
    );
  }

  setLampStateImage(state: number): void {
    switch (state) {
      case 1:
        this.currentLampStateImage = 'assets/images/lamp_1.png';
        break;
      case 2:
        this.currentLampStateImage = 'assets/images/lamp_2.png';
        break;
      case 3:
        this.currentLampStateImage = 'assets/images/lamp_3-6.png';
        break;
      case 4:
        this.currentLampStateImage = 'assets/images/lamp_3-6.png';
        break;
      case 5:
        this.currentLampStateImage = 'assets/images/lamp_3-6.png';
        break;
      case 6:
        this.currentLampStateImage = 'assets/images/lamp_3-6.png';
        break;
      default:
        this.currentLampStateImage = 'assets/images/lamp_off.png';
        break;
    }
  }

  updatePSUImage(): void {
    this.currentPSUStateImage = this.currentPSUState
      ? 'assets/svg/lamp/PSU_on.svg'
      : 'assets/svg/lamp/PSU_off.svg';
  }

  getButtonImage(channel: number): string {
    const basePath = 'assets/svg/lamp/';
    if (this.currentLampState === channel) {
      return `${basePath}ch${channel}_on.svg`;
    } else {
      return `${basePath}ch${channel}.svg`;
    }
  }

  isChannelOn(channel: number): boolean {
    return this.currentLampState === channel;
  }
}
