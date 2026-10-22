-- CreateTable
CREATE TABLE "share_cursors" (
    "battle_id" BIGINT NOT NULL,
    "stream_key" TEXT NOT NULL,
    "epoch" BIGINT NOT NULL,
    "seq" BIGINT NOT NULL,
    "gap_count" INTEGER NOT NULL DEFAULT 0,
    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "share_cursors_pkey" PRIMARY KEY ("battle_id","stream_key")
);

-- AddForeignKey
ALTER TABLE "share_cursors" ADD CONSTRAINT "share_cursors_battle_id_fkey" FOREIGN KEY ("battle_id") REFERENCES "battles"("id") ON DELETE CASCADE ON UPDATE NO ACTION;
