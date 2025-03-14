// error-notification.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject, of } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { catchError, tap } from 'rxjs/operators';

export interface AppError {
  code: string;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class ErrorNotificationService {
  private errorsSubject = new BehaviorSubject<AppError[]>([]);
  errors$ = this.errorsSubject.asObservable();

  private errorMapping: { [code: string]: string } = {};

  constructor(private http: HttpClient) {}

  loadErrorMapping(): Promise<void> {
    return this.http.get<{ [code: string]: string }>('assets/error_messages.json')
      .pipe(
        tap(mapping => { this.errorMapping = mapping; }),
        catchError((error) => {
          console.error('Failed to load error mapping:', error);
          // Even if loading fails, we use an empty mapping
          this.errorMapping = {};
          return of({});
        })
      ).toPromise().then(() => { });
  }

  getMessage(code: string): string {
    return this.errorMapping[code] ||
           this.errorMapping['GENERIC'] ||
           'An error occurred.';
  }

  addError(error: AppError): void {
    const currentErrors = this.errorsSubject.value;
    if (!currentErrors.find(err => err.code === error.code)) {
      // If the provided message is empty, fill it in using our mapping.
      if (!error.message) {
        error.message = this.getMessage(error.code);
      }
      this.errorsSubject.next([...currentErrors, error]);
    }
  }
  
  removeError(code: string): void {
    const currentErrors = this.errorsSubject.value.filter(err => err.code !== code);
    this.errorsSubject.next(currentErrors);
  }
}
