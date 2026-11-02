import { CanActivate, Router, UrlTree } from '@angular/router';
import { AuthenticationService } from '../services/authentication.service';
import { inject, Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class AdminGuard implements CanActivate {
  private authService = inject(AuthenticationService);
  private router = inject(Router);

  canActivate(): boolean | UrlTree {
    const user = this.authService.getUser();

    if (!user || !user.role) {
      return this.router.createUrlTree(['/login']);
    }

    return user.role === 'Admin' ? true : this.router.createUrlTree(['/main']);
  }
}
