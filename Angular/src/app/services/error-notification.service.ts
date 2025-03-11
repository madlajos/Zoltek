import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ErrorNotificationService {
  private errorsSubject = new BehaviorSubject<string[]>([]);
  errors$ = this.errorsSubject.asObservable();

  addError(message: string): void {
    const currentErrors = this.errorsSubject.value;
    // Only add the error if it doesn't already exist
    if (!currentErrors.includes(message)) {
      this.errorsSubject.next([...currentErrors, message]);
    }
  }
  
  removeError(message: string): void {
    const currentErrors = this.errorsSubject.value.filter(err => err !== message);
    this.errorsSubject.next(currentErrors);
  }
}
