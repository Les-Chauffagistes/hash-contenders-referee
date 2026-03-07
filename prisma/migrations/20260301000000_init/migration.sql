-- CreateTable
CREATE TABLE "battles" (
    "id" BIGSERIAL NOT NULL,
    "start_height" INTEGER NOT NULL,
    "rounds" INTEGER NOT NULL,
    "contenders_pv" INTEGER NOT NULL,
    "contender_1_address" TEXT NOT NULL,
    "contender_2_address" TEXT NOT NULL,
    "contender_1_name" TEXT NOT NULL,
    "contender_2_name" TEXT NOT NULL,
    "is_finished" BOOLEAN NOT NULL DEFAULT false,
    "are_addresses_privates" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "battles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rounds" (
    "battle_id" BIGINT NOT NULL,
    "block_height" INTEGER NOT NULL,
    "contender_1_best_diff" INTEGER NOT NULL DEFAULT 0,
    "contender_2_best_diff" INTEGER NOT NULL DEFAULT 0,
    "winner" SMALLINT,
    "damage" INTEGER,
    "finalized_at" TIMESTAMP(6),

    CONSTRAINT "rounds_pkey" PRIMARY KEY ("battle_id","block_height")
);

-- AddForeignKey
ALTER TABLE "rounds" ADD CONSTRAINT "rounds_battle_id_fkey" FOREIGN KEY ("battle_id") REFERENCES "battles"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;
