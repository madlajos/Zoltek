import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { ErrorNotificationService } from '../../services/error-notification.service';
import { switchMap } from 'rxjs/operators';


@Component({
  standalone: true,
  selector: 'app-turntable-control',
  templateUrl: './turntable-control.component.html',
  styleUrls: ['./turntable-control.component.css'],
  imports: [CommonModule, MatIconModule]
})
export class TurntableControlComponent implements OnInit, OnDestroy {
  private readonly BASE_URL = 'http://localhost:5000/api';
  movementAmount: number = 1;
  turntablePosition: number | string = '?';
  connectionPolling: Subscription | undefined;
  reconnectionPolling: Subscription | undefined;
  isConnected: boolean = false;
  isEditingPosition: boolean = false;
  isHomed: boolean = false;

  constructor(
    private http: HttpClient,
    private errorNotificationService: ErrorNotificationService
  ) {}

  ngOnInit(): void {
    this.startConnectionPolling();
  }

  ngOnDestroy(): void {
    this.stopConnectionPolling();
    this.stopReconnectionPolling();
  }

  startConnectionPolling(): void {
    if (!this.connectionPolling) {
      this.connectionPolling = interval(5000)
        .pipe(
          switchMap(() =>
            this.http.get<{ connected: boolean }>(`${this.BASE_URL}/status/serial/turntable`)
          )
        )
        .subscribe({
          next: (response) => {
            const wasConnected = this.isConnected;
            this.isConnected = response.connected;
            if (!this.isConnected && !this.reconnectionPolling) {
              console.warn("Turntable disconnected – starting reconnection polling.");
              this.errorNotificationService.addError({
                code: "E1203",
                message: this.errorNotificationService.getMessage("E1203")
              });
              this.stopConnectionPolling();
              this.startReconnectionPolling();
            } else if (this.isConnected && !wasConnected) {
              console.info("Turntable reconnected.");
              this.errorNotificationService.removeError("E1203");
              this.stopReconnectionPolling();
              this.startConnectionPolling();
            }
          },
          error: (error) => {
            console.error('Failed to check turntable connection!', error);
            if (!this.reconnectionPolling) {
              this.errorNotificationService.addError({
                code: "E1203",
                message: this.errorNotificationService.getMessage("E1203")
              });
              this.stopConnectionPolling();
              this.startReconnectionPolling();
            }
            this.isConnected = false;
          }
        });
    }
  }

  stopConnectionPolling(): void {
    if (this.connectionPolling) {
      this.connectionPolling.unsubscribe();
      this.connectionPolling = undefined;
    }
  }

  startReconnectionPolling(): void {
    if (!this.reconnectionPolling) {
      this.reconnectionPolling = interval(3000).subscribe(() => {
        this.tryReconnectTurntable();
      });
    }
  }

  stopReconnectionPolling(): void {
    this.reconnectionPolling?.unsubscribe();
    this.reconnectionPolling = undefined;
  }

  tryReconnectTurntable(): void {
    this.http.post<{ message: string }>(`${this.BASE_URL}/connect-to-turntable`, {}).subscribe({
      next: (response) => {
        console.info('Turntable reconnected:', response.message);
        this.isConnected = true;
        this.errorNotificationService.removeError("E1203");
        this.stopReconnectionPolling();
        this.startConnectionPolling();
      },
      error: (error) => {
        console.warn('Turntable reconnection attempt failed.', error);
      }
    });
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
        
        // Only update if it's NOT "?"
        if (response.current_position !== '?') {
          this.turntablePosition = response.current_position;
        } else {
          this.turntablePosition = '?'; 
        }
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

homeTurntable(): void {
  this.http.post(`${this.BASE_URL}/home_turntable_with_image`, {}).subscribe(
    (response: any) => {
      console.log('Homing successful:', response);
      this.turntablePosition = response.current_position;
    },
    (error) => {
      console.error('Failed to home turntable!', error);
    }
  );
}

  setMovementAmount(amount: number): void {
    this.movementAmount = amount;
    console.log('Movement amount set to', this.movementAmount);
  }

  formatPosition(pos: number | string): string {
    if (pos === '?') {
      return '?'; // Not homed
    }
    const numericValue = Number(pos);
    if (isNaN(numericValue)) {
      console.error('Invalid position value:', pos);
      return '?';
    }
    return numericValue.toFixed(1) + '°';
  }

  onFocus(): void {
    this.isEditingPosition = true;
  }

  onBlur(): void {
    this.isEditingPosition = false;
  }
}