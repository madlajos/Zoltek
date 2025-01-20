import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-turntable-control',
  templateUrl: './turntable-control.component.html',
  styleUrls: ['./turntable-control.component.css']
})
export class TurntableControlComponent implements OnInit, OnDestroy {
  private readonly BASE_URL = 'http://localhost:5000';
  movementAmount: number = 1; // Default movement amount

  turntablePosition: number | string = '?';  // Default unknown position
  positionPolling: Subscription | undefined; // Subscription for polling turntable position
  connectionPolling: Subscription | undefined; // Subscription for polling turntable controller connection status
  isConnected: boolean = false; // Track the connection status of the turntable controller
  isEditingPosition: boolean = false; // Flag to track if the position input is being edited
  isHomed: boolean = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.startConnectionPolling();
  }

  ngOnDestroy(): void {
    this.stopConnectionPolling();
  }

  startConnectionPolling(): void {
    this.connectionPolling = interval(5000).subscribe(() => {
      this.checkTurntableConnection();
    });
  }

  stopConnectionPolling(): void {
    this.connectionPolling?.unsubscribe();
  }

  checkTurntableConnection(): void {
    this.http.get<{ connected: boolean }>(`${this.BASE_URL}/api/status/turntable`).subscribe(
      (response) => {
        const wasConnected = this.isConnected;
        this.isConnected = response.connected;
      },
      (error) => {
        console.error('Failed to check printer connection status!', error);
        this.isConnected = false;
      }
    );
  }

  updateTurntablePosition(): void {
    if (this.isConnected) {
      this.http.get<{ position: number }>(`${this.BASE_URL}/get_turntable_position`).subscribe(
        (position) => {
          if (!this.isEditingPosition) {
            this.turntablePosition = position.position;
          }
        },
        (error) => {
          console.error('Failed to get turntable position!', error);
        }
      );
    }
  }

  moveTurntableRelative(degrees: number): void {
    const payload = { degrees };
    this.http.post(`${this.BASE_URL}/move_turntable_relative`, payload).subscribe(
      (response: any) => {
        console.log('Turntable moved successfully!', response.message);
        this.turntablePosition = response.current_position;  // Update position only after homing
      },
      (error: any) => {
        console.error('Failed to move turntable relative!', error);
      }
    );
  }

moveTurntableAbsolute(position: number | string): void {
    // Convert input to number safely
    const degrees = typeof position === 'number' ? position : Number(position);
    if (isNaN(degrees)) {
      console.error('Invalid position input');
      return;
    }

    const payload = { degrees };
    this.http.post(`${this.BASE_URL}/move_turntable_absolute`, payload).subscribe(
      (response: any) => {
        console.log('Turntable moved to position successfully!', response.message);
        this.turntablePosition = response.current_position;
      },
      (error: any) => {
        console.error('Failed to move turntable to specified position!', error);
      }
    );
}


//TODO: Add normal funcionality
homeTurntable(): void {
  this.http.post(`${this.BASE_URL}/home_turntable`, {}).subscribe(
    (response: any) => {
      console.log('Turntable homed successfully!', response);
      this.turntablePosition = 0;  // Set position to 0 after homing
      this.isHomed = true;  // Enable tracking after homing
    },
    (error: any) => {
      console.error('Failed to home turntable!', error);
    }
  );
}


  setMovementAmount(amount: number): void {
    this.movementAmount = amount;
    console.log('Movement amount set to', this.movementAmount);
  }


  onFocus(): void {
    this.isEditingPosition = true;
  }

  onBlur(): void {
    this.isEditingPosition = false;
  }
}
