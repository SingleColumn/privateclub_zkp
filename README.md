## Private Club ZKP

This repo has prototypes for two components of a mobile app to produce secure and private proof of funds credentials that can be shared with other members of a private club.

This repo has two main pieces:
- **Member UI mocks**: React/Vite mock screens for members generating and sharing proof-of-funds credentials.
- **ZKP engine simulation**: Python simulation of the zero-knowledge proof engine that verifies a member has funds above a chosen threshold.

### Run the member UI mocks

```bash
cd member-ui-mocks
npm install
npm run dev
```

Then open the local URL shown in the terminal (for example `http://localhost:5173`).

### Run the ZKP engine simulation

From the project root:

```bash
python zkp_simulation.py
```

Follow the prompts to run manual checks or predefined scenarios against the ZKP engine.

