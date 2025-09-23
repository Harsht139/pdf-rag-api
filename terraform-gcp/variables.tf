variable "project_id" {
  description = "The project ID to host the service account in"
  type        = string
}

variable "service_account_name" {
  description = "The name of the service account"
  type        = string
}

variable "impersonation_user_email" {
  description = "The email address of the user who can impersonate the service account."
  type        = string
  default     = ""
}