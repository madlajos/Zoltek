// src/app/interceptors/popup.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, tap, throwError } from 'rxjs';
import { HttpRequest, HttpHandlerFn, HttpEvent, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ErrorNotificationService } from '../services/error-notification.service';

interface ApiResponse {
  popup?: boolean;
  error?: string;
}

export const popupInterceptor: HttpInterceptorFn = (
  req: HttpRequest<any>,
  next: HttpHandlerFn
): Observable<HttpEvent<any>> => {
  const errorNotificationService = inject(ErrorNotificationService);

  return next(req).pipe(
    tap((event) => {
      if (event instanceof HttpResponse) {
        const body = event.body as ApiResponse;
        if (body?.popup) {
          // Forward error message to the notification service
          errorNotificationService.addError(body.error || 'An error occurred.');
        }
      }
    }),
    catchError((error: HttpErrorResponse) => {
      const errorBody = error.error as ApiResponse;
      if (errorBody?.popup) {
        errorNotificationService.addError(errorBody.error || 'An error occurred.');
      }
      return throwError(() => error);
    })
  );
};
