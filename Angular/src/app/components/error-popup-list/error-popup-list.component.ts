import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ErrorNotificationService, AppError } from '../../services/error-notification.service';
import { Observable } from 'rxjs';
import { ErrorPopupComponent } from '../error-popup/error-popup.component';

@Component({
  selector: 'app-error-popup-list',
  standalone: true,
  imports: [CommonModule, ErrorPopupComponent],
  templateUrl: './error-popup-list.component.html',
  styleUrls: ['./error-popup-list.component.css']
})
export class ErrorPopupListComponent {
  errors$: Observable<AppError[]>;

  constructor(private errorNotificationService: ErrorNotificationService) {
    this.errors$ = this.errorNotificationService.errors$;
  }
}
