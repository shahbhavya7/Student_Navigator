-- CreateTable
CREATE TABLE "interventions" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "interventionType" TEXT NOT NULL,
    "priority" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "context" JSONB NOT NULL,
    "deliveredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "acknowledgedAt" TIMESTAMP(3),
    "effectiveness" DOUBLE PRECISION,
    "outcome" TEXT,

    CONSTRAINT "interventions_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "interventions_studentId_deliveredAt_idx" ON "interventions"("studentId", "deliveredAt");

-- CreateIndex
CREATE INDEX "interventions_sessionId_idx" ON "interventions"("sessionId");

-- AddForeignKey
ALTER TABLE "interventions" ADD CONSTRAINT "interventions_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "students"("id") ON DELETE CASCADE ON UPDATE CASCADE;
