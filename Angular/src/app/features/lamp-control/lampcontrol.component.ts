import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-lamp-control',
  templateUrl: './lamp-control.component.html',
  styleUrls: ['./lamp-control.component.css']
})
export class LampControlComponent implements OnInit {
  private readonly BASE_URL = 'http://localhost:5000/api';
  currentLampStateImage: string = 'assets/images/lamp_off.png';
  lampStatePolling: Subscription | undefined;
  settings: any;
  currentLampState: number = -1; // Track the current lamp state

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    this.loadSettings();
    this.updateLampState();
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

  pollLampState(): void {
    if (this.lampStatePolling) {
      this.lampStatePolling.unsubscribe();
    }

    this.lampStatePolling = interval(500).subscribe(() => {
      this.updateLampState();
    });
  }

  updateLampState(): void {
    this.http.get<number>(`${this.BASE_URL}/get-lamp-state`).subscribe(
      (state) => {
        this.currentLampState = state;
        this.setLampStateImage(state);
      },
      (error) => {
        console.error('Failed to get lamp state', error);
        this.currentLampState = -1; // Default to lamp off in case of error
        this.setLampStateImage(-1);
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
