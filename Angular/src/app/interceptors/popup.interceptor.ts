// popup.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, tap, throwError } from 'rxjs';
import { HttpRequest, HttpHandlerFn, HttpEvent, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ErrorNotificationService, AppError } from '../services/error-notification.service';

interface ApiResponse {
  popup?: boolean;
  error?: string;
  code?: string;
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
          const code = body.code || 'GENERIC';
          const message = errorNotificationService.getMessage(code);
          console.debug("Interceptor tap: adding error", { code, message });
          errorNotificationService.addError({ code, message });
        }
      }
    }),
    catchError((error: HttpErrorResponse) => {
      console.error("Interceptor caught error:", error);
      const errorBody = error.error as ApiResponse;
      console.debug("Error body in interceptor:", errorBody);
      const code = errorBody?.code || 'GENERIC';
      const message = errorNotificationService.getMessage(code);
      console.debug("Interceptor catchError: adding error", { code, message });
      errorNotificationService.addError({ code, message });
      return throwError(() => error);
    })
  );
};
