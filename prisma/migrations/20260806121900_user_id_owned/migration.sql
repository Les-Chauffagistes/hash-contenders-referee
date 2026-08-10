/*
  Warnings:

  - Added the required column `owner_user_id` to the `battles` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "battles" ADD COLUMN     "owner_user_id" BIGINT NOT NULL;
