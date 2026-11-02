import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { concatMap, EMPTY, finalize, Observable, of, throwError } from 'rxjs';

import { AuthenticationService } from '@app/auth/services/authentication.service';
import { UserModel } from '@app/auth/models/user.model';
import { UsersService } from '@app/services/users/users.service';
import { ToastService } from '@app/services/toast/toast.service';

type ProfileControlName = 'firstName' | 'lastName';

@Component({
  selector: 'app-general-user-info',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: 'general-user-info.component.html',
  styleUrl: 'general-user-info.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GeneralInformationComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly usersService = inject(UsersService);
  private readonly toastService = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly user = signal<UserModel | null>(null);
  readonly profileImage = signal<string | null>(null);
  readonly isSaving = signal(false);
  readonly isReadingPhoto = signal(false);

  private photoChanged = false;
  private imageRevision = 0;
  private userRevision = 0;
  private savedFirstName = '';
  private savedLastName = '';
  private activeReader: FileReader | null = null;
  private activeImage: HTMLImageElement | null = null;

  readonly userForm = this.formBuilder.nonNullable.group({
    firstName: [
      '',
      [Validators.required, Validators.maxLength(50), Validators.pattern(/^[A-Za-z'-]+$/)],
    ],
    lastName: [
      '',
      [Validators.required, Validators.maxLength(50), Validators.pattern(/^[A-Za-z'-]+$/)],
    ],
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.imageRevision++;
      this.stopReadingPhoto();
    });

    this.authenticationService.user$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((user) => {
      const userChanged = this.user()?.id !== user?.id;
      this.user.set(user);

      if (userChanged) {
        this.userRevision++;
        this.imageRevision++;
        this.stopReadingPhoto();
        this.photoChanged = false;
        this.profileImage.set(null);
        this.savedFirstName = user?.firstName ?? '';
        this.savedLastName = user?.lastName ?? '';
      }

      if (!user) {
        this.userForm.reset();
        return;
      }

      this.userForm.patchValue({
        firstName: user.firstName,
        lastName: user.lastName,
      });

      if (userChanged) {
        this.loadUserProfileImage(user.id);
      }
    });
  }

  isInvalid(controlName: ProfileControlName): boolean {
    const control = this.userForm.controls[controlName];
    return control.invalid && control.touched;
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';

    if (!file || !this.user()) {
      return;
    }

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      this.showError('Please select a JPEG, PNG, or WebP image');
      return;
    }

    if (file.size === 0) {
      this.showError('Please select a non-empty image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      this.showError('Image must be 5 MB or smaller');
      return;
    }

    const revision = ++this.imageRevision;
    this.stopReadingPhoto();

    const reader = new FileReader();
    this.activeReader = reader;
    this.isReadingPhoto.set(true);

    reader.onload = () => {
      if (this.activeReader !== reader || revision !== this.imageRevision) {
        return;
      }

      this.activeReader = null;

      if (typeof reader.result !== 'string') {
        this.handlePhotoReadError();
        return;
      }

      this.validateImage(reader.result, revision);
    };

    reader.onerror = () => {
      if (this.activeReader !== reader || revision !== this.imageRevision) {
        return;
      }

      this.activeReader = null;
      this.isReadingPhoto.set(false);
      this.handlePhotoReadError();
    };

    reader.readAsDataURL(file);
  }

  onSave(): void {
    if (this.isSaving() || this.isReadingPhoto()) {
      return;
    }

    const user = this.user();
    if (!user) {
      return;
    }

    if (this.userForm.invalid) {
      this.userForm.markAllAsTouched();
      return;
    }

    const { firstName, lastName } = this.userForm.getRawValue();
    const imageToUpload = this.photoChanged ? this.profileImage() : null;
    const namesChanged = firstName !== this.savedFirstName || lastName !== this.savedLastName;
    if (!namesChanged && !imageToUpload) {
      return;
    }

    const imageRevision = this.imageRevision;
    const userRevision = this.userRevision;
    let uploadingPhoto = false;
    let savingNames = false;

    this.isSaving.set(true);

    const saveNames$: Observable<unknown> = namesChanged
      ? this.authenticationService.editProfile(firstName, lastName).pipe(
          concatMap((response) => {
            if (!response) {
              return throwError(() => new Error('Failed to update profile'));
            }

            savingNames = true;
            this.savedFirstName = firstName;
            this.savedLastName = lastName;
            return of(response);
          })
        )
      : of(null);

    saveNames$
      .pipe(
        concatMap(() => {
          if (userRevision !== this.userRevision) {
            return EMPTY;
          }

          if (!imageToUpload) {
            return of(null);
          }

          uploadingPhoto = true;
          return this.authenticationService.uploadMyProfileImage(imageToUpload);
        }),
        finalize(() => this.isSaving.set(false)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: () => {
          if (userRevision !== this.userRevision) {
            return;
          }

          if (imageToUpload && imageRevision === this.imageRevision) {
            this.photoChanged = false;
          }

          this.showSuccess();
        },
        error: (error: unknown) => {
          if (userRevision !== this.userRevision) {
            return;
          }

          if (uploadingPhoto) {
            console.error('Failed to upload profile image', error);
            this.showError(
              savingNames
                ? 'Your name changes were saved, but the photo upload failed. Click Save Changes to retry the photo.'
                : 'Failed to upload profile image'
            );
          } else {
            this.showError();
          }
        },
      });
  }

  private loadUserProfileImage(userId: string): void {
    const revision = this.imageRevision;

    this.usersService
      .getUserProfileImage(userId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          if (revision !== this.imageRevision || this.photoChanged) {
            return;
          }

          this.profileImage.set(response.presignedUrl);
        },
        error: (error: unknown) => {
          if (revision !== this.imageRevision || this.photoChanged) {
            return;
          }

          console.error('Failed to load profile image', error);
          this.profileImage.set(null);
        },
      });
  }

  private stopReadingPhoto(): void {
    const reader = this.activeReader;
    this.activeReader = null;
    this.activeImage = null;
    this.isReadingPhoto.set(false);

    if (reader?.readyState === FileReader.LOADING) {
      reader.abort();
    }
  }

  private handlePhotoReadError(): void {
    this.isReadingPhoto.set(false);
    this.showError('Failed to read profile image');

    const user = this.user();
    if (user && !this.photoChanged && !this.profileImage()) {
      this.loadUserProfileImage(user.id);
    }
  }

  private validateImage(imageData: string, revision: number): void {
    const image = new Image();
    this.activeImage = image;

    image.onload = () => {
      if (this.activeImage !== image || revision !== this.imageRevision) {
        return;
      }

      this.activeImage = null;
      this.isReadingPhoto.set(false);
      if (image.naturalWidth > 4096 || image.naturalHeight > 4096) {
        this.showError('Image dimensions must not exceed 4096 × 4096 pixels');
        return;
      }

      this.photoChanged = true;
      this.profileImage.set(imageData);
    };

    image.onerror = () => {
      if (this.activeImage !== image || revision !== this.imageRevision) {
        return;
      }

      this.activeImage = null;
      this.isReadingPhoto.set(false);
      this.showError('Please select a valid image file');
    };

    image.src = imageData;
  }

  private showSuccess(): void {
    this.toastService.success('Profile updated successfully', 'Success');
  }

  private showError(message = 'Failed to update profile'): void {
    this.toastService.error(message, 'Error');
  }
}
