-- DropForeignKey
ALTER TABLE "rounds" DROP CONSTRAINT "rounds_battle_id_fkey";

-- AddForeignKey
ALTER TABLE "rounds" ADD CONSTRAINT "rounds_battle_id_fkey" FOREIGN KEY ("battle_id") REFERENCES "battles"("id") ON DELETE CASCADE ON UPDATE NO ACTION;
