# Fermentation dynamic-prediction profile

Use only for reviews about fermentation modeling, digital twins, and prediction under changing operating conditions.

## Core distinctions

| Distinction | Question to answer |
|---|---|
| Fitting vs prediction | Are model parameters estimated from observed trajectories, or is a future trajectory predicted without using its outcomes? |
| Interpolation vs extrapolation | Are test states within the training domain, or does the test use unseen conditions/policies? |
| State estimation vs forecasting | Does the method update hidden states using current measurements, or forecast without future observations? |
| Batch holdout vs policy holdout | Is a new batch held out, and are feed/induction/temperature policies themselves novel? |
| Mechanistic vs data-driven vs hybrid | Which structure comes from balances/kinetics, data, or their coupling? |

## Hybrid-model families

- **Rate learning**: learn kinetic rates or rate corrections while integrating a mechanistic state model.
- **Parameter learning**: predict condition-dependent parameters that enter mechanistic equations.
- **State correction**: update latent process states from measurements, such as filtering or moving-horizon estimation.
- **Output residual correction**: correct predicted outputs after the mechanistic trajectory is calculated.
- **Coupled/hierarchical methods**: share information between physical states, learned components, and measurements through another explicit architecture.

Do not place a method in a family from its label alone; inspect equations, data flow, and what is learned.

## Minimum comparison fields

Record organism/strain, reactor scale and configuration, batch/fed-batch/continuous mode, measured variables, latent states, input trajectories, feed composition, initial conditions, sampling frequency, model structure, training batches, validation split, unseen operating-policy status, forecast horizon, error metrics, physical constraints, uncertainty, and experimental replication.

## Evidence and interpretation

- Treat a random time-point split within one batch as trajectory interpolation unless the design demonstrates otherwise.
- Distinguish observed process interventions from simulated scenarios and model-based recommendations.
- Check whether reported feed rates, induction settings, and temperature profiles are available to the predictor at inference time.
- Compare error metrics only when targets, units, scales, forecast horizons, and split designs are compatible.
- Keep claims about online control, real-time deployment, or scale-up within the evidence actually demonstrated.
- Research-gap statements must be bounded by documented search terms, databases, years, and accessible full texts.
