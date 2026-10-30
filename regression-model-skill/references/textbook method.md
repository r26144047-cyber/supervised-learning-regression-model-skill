# Supervised Learning: Linear Models and Regularization Methods

Linear · Polynomial · Logistic · Ridge · Lasso

## 閱讀方式

每個方法按照：**符號 → 使用前提 → 模型 → 適用情境／限制**。

## 數學符號

| 符號              | 意義                            |
|-------------------|---------------------------------|
| $n$               | 樣本數                          |
| $p$               | 解釋變數數量（不含截距）        |
| $Y_i$             | 第 $i$ 筆結果變數               |
| $X_{ij}$          | 第 $i$ 筆、第 $j$ 個解釋變數    |
| $\beta_j$         | 未知迴歸係數                    |
| $\varepsilon_i$   | 隨機誤差                        |
| $\hat Y_i$、$e_i$ | 預測值、殘差 $e_i=Y_i-\hat Y_i$ |

## 研究問題

| 結果 $Y$       | 研究目的               | 候選方法   |
|----------------|------------------------|------------|
| 連續數值       | 近似直線的條件平均     | Linear     |
| 連續數值       | 平滑曲線的條件平均     | Polynomial |
| 二元 $\{0,1\}$ | 事件機率               | Logistic   |
| 連續數值       | 收縮係數、緩解不穩定   | Ridge      |
| 連續數值       | 收縮係數、產生稀疏模型 | Lasso      |

**Ridge／Lasso 是懲罰方式，也能擴展至 Logistic。**

## 0.1 多重共線性（Multicollinearity）

當解釋變數之間存在高度線性關係時，可能造成迴歸係數估計不穩定、標準誤增大。

使用 **Variance Inflation Factor（VIF）** 衡量共線性程度：

$$VIF_j=\frac{1}{1-R_j^2}
$$

其中 $R_j^2$ 為將第 $j$ 個解釋變數對其他解釋變數進行迴歸所得的判定係數。

**常見判斷準則：**

| VIF           | 共線性程度         |
|---------------|--------------------|
| $VIF=1$       | 無線性共線性       |
| $1<VIF<5$     | 通常可接受         |
| $5\le VIF<10$ | 可能存在較高共線性 |
| $VIF\ge10$    | 嚴重共線性警訊     |

**注意：** VIF 門檻為經驗準則

## 0.2 完全分離（Complete Separation）

完全分離主要發生於 **Logistic Regression**。

若存在非零向量 $\boldsymbol b$，使得：

$$
\begin{cases}
\mathbf x_i^\top\boldsymbol b>0, & Y_i=1,\\
\mathbf x_i^\top\boldsymbol b<0, & Y_i=0,
\end{cases}
$$

則稱為完全分離，表示解釋變數可以完全區分兩類結果。

**判斷準則：**

| 情況                                                       | 判斷                      |
|------------------------------------------------|------------------------|
| 存在嚴格線性分離邊界                                       | Complete Separation       |
| 存在非嚴格分離方向，部分觀測值位於邊界，且至少有嚴格不等式 | Quasi-complete Separation |
| 不存在上述分離方向                                         | 無完全或準完全分離        |

**影響：** 完全分離或準完全分離時，一般Logistic Regression的有限最大概似估計可能不存在，係數可能趨向無限大。

**處理方式：** 可考慮 Ridge-penalized Logistic Regression或 Lasso Logistic Regression。

## 0.3 變異數同質性（Homoscedasticity）

線性迴歸假設誤差項在不同解釋變數條件下具有相同的變異數，即：

$$
\operatorname{Var}(\varepsilon_i\mid X_i)=\sigma^2
$$

若誤差項的變異數隨解釋變數而改變，則稱為**異質變異數（Heteroscedasticity）**。在其他迴歸假設成立的情況下，異質變異數不會使普通最小平方法（OLS）的係數估計產生偏誤，但可能使傳統標準誤估計不正確，進而影響信賴區間、$t$ 檢定與 $F$ 檢定的可靠性。

**檢查方式：**

先繪製「殘差對預測值散佈圖」。若殘差的散布寬度大致一致，通常符合變異數同質性；若呈現漏斗形或扇形，則可能存在異質變異數。

正式檢定可使用 **Breusch–Pagan 檢定（BP 檢定）**；若希望檢查更一般的變異數變化，例如與解釋變數的平方項及交互作用有關的情況，可使用 **White 檢定**。

兩者的假設皆為：

-   $H_0$：誤差項具有同質變異數。
-   $H_1$：誤差項存在異質變異數。

**常見判斷準則（顯著水準** $\alpha=0.05$）：

| 檢定結果   | 判斷                                         |
|------------|----------------------------------------------|
| $p\ge0.05$ | 不拒絕 $H_0$，尚無足夠證據認為存在異質變異數 |
| $p<0.05$   | 拒絕 $H_0$，有證據顯示存在異質變異數         |

未達顯著不代表已證明變異數相同，仍應搭配殘差圖判讀。若發現異質變異數，可採用**異質變異數穩健標準誤**，或依資料特性考慮應變數轉換、加權最小平方法等處理方式。

## 0.4 誤差常態性（Normality of Errors）

線性迴歸的常態性假設，是指在給定解釋變數的條件下，誤差項服從常態分布：

$$
\varepsilon_i\mid X_i\sim N(0,\sigma^2)
$$

由於誤差項無法直接觀察，實務上會使用**殘差**進行診斷。常態性主要影響小樣本下傳統 $t$ 檢定、$F$ 檢定與信賴區間的精確性，並非 OLS 係數估計不偏的必要條件。

**檢查方式：**

可先使用 **Q–Q 圖**觀察殘差是否大致沿直線排列，正式檢定再搭配 **Shapiro–Wilk 檢定**或 **Jarque–Bera 檢定**。

-   $H_0$：誤差項服從常態分布。
-   $H_1$：誤差項不服從常態分布。

**常見判斷準則（顯著水準** $\alpha=0.05$）：

| 檢查方式   | 判斷標準                                                                   |
|------------------------------------|------------------------------------|
| Q–Q 圖     | 點大致沿直線排列，表示分布接近常態；明顯彎曲或尾端偏離，可能表示偏態或厚尾 |
| $p\ge0.05$ | 不拒絕 $H_0$，尚無足夠證據認為誤差不服從常態分布                           |
| $p<0.05$   | 拒絕 $H_0$，有證據顯示誤差偏離常態分布                                     |

上述檢定用於迴歸殘差時屬於診斷工具，應搭配圖形判讀。大樣本下，輕微偏離常態也可能達到統計顯著；若發現異常，應進一步檢查離群值、模型設定與資料分布。

## 0.5 誤差獨立性（Independence of Errors）

誤差獨立性是指，在給定解釋變數的條件下，不同觀測值的誤差項彼此獨立。獨立性意味著誤差不相關，即在變異數存在時：

$$
\operatorname{Cov}(\varepsilon_i,\varepsilon_j\mid X)=0,
\qquad i\ne j
$$

但**誤差不相關不一定代表彼此獨立**。本書主要討論誤差項之間的相關性，指出此問題常見於時間序列資料，也可能出現在同一家族或共享環境的觀測資料中。

若忽略誤差相關性，傳統標準誤可能估計不正確。例如，在正相關的情況下，可能低估標準誤，使信賴區間過窄，並高估統計顯著性。

**檢查方式：**

將殘差依時間或有意義的觀測順序繪圖。若殘差沒有明顯規律，則未觀察到明顯的序列相關；若相鄰殘差經常具有相似數值，或呈現連續上升、下降與週期變化，則可能存在相關性。

**可使用的正式檢定**

對於具有時間順序的資料，可搭配以下檢定檢查序列相關：

| 檢定方法                 | 檢查內容             | 判斷標準                                                                      |
|------------------------|------------------------|------------------------|
| **Durbin–Watson 檢定**   | 一階自相關           | 統計量接近 2 表示沒有明顯一階自相關；小於 2 偏向正自相關，大於 2 偏向負自相關 |
| **Breusch–Godfrey 檢定** | 指定階數內的序列相關 | $p<0.05$ 時，拒絕無自相關的虛無假設                                           |

Durbin–Watson 統計量為：

$$
DW=\frac{\sum_{t=2}^{n}(e_t-e_{t-1})^2}
{\sum_{t=1}^{n}e_t^2}
$$

其中，$e_t$ 為第 $t$ 筆觀測值的殘差。正式判斷須依適用的臨界值或檢定結果，不能僅以「接近 2」作為通用通過標準。傳統 Durbin–Watson 檢定不適用於包含落後應變數的模型，此時可考慮 Breusch–Godfrey 檢定。

Breusch–Godfrey 檢定的假設為：

-   $H_0$：誤差項在指定階數內無自相關。
-   $H_1$：誤差項在指定階數內存在自相關。

**常見判斷準則（顯著水準** $\alpha=0.05$）：

| 檢定結果   | 判斷                                                   |
|------------|--------------------------------------------------------|
| $p\ge0.05$ | 不拒絕 $H_0$，尚無足夠證據認為存在指定階數內的自相關   |
| $p<0.05$   | 拒絕 $H_0$，有證據顯示存在自相關，獨立性假設可能不成立 |

上述檢定只能檢查特定形式的序列相關，**不能證明誤差完全獨立**。若資料為重複測量或群組資料，還須依研究設計與群組結構判斷，不能僅依序列相關檢定確認獨立性。

# 1. Linear Regression

## 1.1 資料與模型

對 $i=1,\ldots,n$：

$$Y_i=\beta_0+\sum_{j=1}^{p}\beta_jX_{ij}+\varepsilon_i$$

令 $\mathbf x_i=(1,X_{i1},\ldots,X_{ip})^\top$，則

$$Y_i=\mathbf x_i^\top\boldsymbol\beta+\varepsilon_i$$

若 $E(\varepsilon_i\mid\mathbf X)=0$：

$$E(Y_i\mid\mathbf X)=\mathbf x_i^\top\boldsymbol\beta$$

## 1.2 使用前提｜模型與可識別性

| 條件           | 數學表述                             | 不成立時               |
|------------------|---------------------------------|---------------------|
| 設計矩陣滿列秩 | $\operatorname{rank}(\mathbf X)=p+1$ | OLS 係數不能唯一識別   |
| 有足夠觀測資訊 | 通常 $n\ge p+1$，且滿秩              | 無法以一般公式唯一估計 |

## 1.3 使用前提｜傳統推論

傳統同質變異、無相關誤差條件：

$$\operatorname{Var}(\boldsymbol\varepsilon\mid\mathbf X)=\sigma^2\mathbf I_n$$

若有常態假設：

$$\boldsymbol\varepsilon\mid\mathbf X\sim N_n(\mathbf 0,\sigma^2\mathbf I_n),$$

可建立小樣本精確的 $t$ 與 $F$ 推論。

-   **異質變異：** 不必停止 OLS；可改用異質變異穩健標準誤(例:使用Huber–White Sandwich Estimator)。

-   **非常態：**不影響 OLS 公式；小樣本常態理論推論可能失效。

## 1.4 Step 1｜定義 OLS 損失函數

令 $\mathbf Y=(Y_1,\ldots,Y_n)^\top$，$\mathbf X$ 為 $n\times(p+1)$ 設計矩陣。

$$\mathbf Y=\mathbf X\boldsymbol\beta+\boldsymbol\varepsilon$$

最小化殘差平方和：

$$S(\boldsymbol\beta)=\sum_{i=1}^n(Y_i-\mathbf x_i^\top\boldsymbol\beta)^2$$

$$=(\mathbf Y-\mathbf X\boldsymbol\beta)^\top(\mathbf Y-\mathbf X\boldsymbol\beta).$$

## 1.5 Step 2｜展開與微分

$$S(\beta)=\mathbf Y^\top\mathbf Y-2\beta^\top\mathbf X^\top\mathbf Y+\beta^\top\mathbf X^\top\mathbf X\beta.$$

對 $\beta$ 求梯度：

$$\nabla_\beta S=-2\mathbf X^\top\mathbf Y+2\mathbf X^\top\mathbf X\beta.$$

令梯度為零：

$$\mathbf X^\top\mathbf X\hat\beta=\mathbf X^\top\mathbf Y.$$

此式稱為 **normal equations（正規方程）**。

## 1.6 Step 3｜求得 OLS 估計量

當 $\operatorname{rank}(\mathbf X)=p+1$，$\mathbf X^\top\mathbf X$ 可逆：

$$\hat\beta_{OLS}=(\mathbf X^\top\mathbf X)^{-1}\mathbf X^\top\mathbf Y$$

代入 $\mathbf Y=\mathbf X\beta+\varepsilon$：

$$\hat\beta_{OLS}=\beta+(\mathbf X^\top\mathbf X)^{-1}\mathbf X^\top\varepsilon$$

故若 $E(\varepsilon\mid\mathbf X)=0$：

$$E(\hat\beta_{OLS}\mid\mathbf X)=\beta$$

## 1.7 Step 4｜估計量的變異數

若 $\operatorname{Var}(\varepsilon\mid\mathbf X)=\sigma^2\mathbf I_n$：

$$\operatorname{Var}(\hat\beta_{OLS}\mid\mathbf X)=\sigma^2(\mathbf X^\top\mathbf X)^{-1}$$

殘差變異估計：

$$\hat\sigma^2=\frac{\sum_{i=1}^n e_i^2}{n-p-1}$$

第 $j$ 個係數的傳統標準誤：

$$SE(\hat\beta_j)=\sqrt{\hat\sigma^2[(\mathbf X^\top\mathbf X)^{-1}]_{jj}}$$

## 1.8 適用情境與限制

| 適合                       | 警訊／限制       |
|----------------------------|------------------|
| 連續結果、近似線性條件平均 | 殘差有系統性曲線 |
| 設計矩陣滿秩               | 完全共線性       |

**優點：** 簡潔、易解釋、可建立完整推論。**限制：** 對模型錯置及極端觀測敏感。

# 2. Polynomial Regression

## 2.1 模型與符號

單一 $X$ 的 $d$ 次多項式：

$$Y_i=\beta_0+\beta_1X_i+\beta_2X_i^2+\cdots+\beta_dX_i^d+\varepsilon_i$$

定義轉換後的特徵：

$$Z_{ik}=X_i^k,\qquad k=1,\ldots,d$$

則 $Y_i=\beta_0+\sum_{k=1}^{d}\beta_kZ_{ik}+\varepsilon_i$，**對係數仍然線性**。

## 2.2 使用前提｜先檢查

| 條件           | 數學表述／判準                       | 不成立時               |
|------------------|---------------------------------|---------------------|
| 轉換後矩陣滿秩 | $\operatorname{rank}(\mathbf Z)=d+1$ | 無法唯一估計全部係數   |
| 有足夠觀測值   | 通常 $n\ge d+1$，且滿秩              | 無法以一般公式唯一估計 |

**高次多項式不宜無限制增加階數；觀測範圍外的外插尤其不可靠。**

## 2.3 Step 1｜二次模型的曲率

$$m(x)=E(Y\mid X=x)=\beta_0+\beta_1x+\beta_2x^2$$

一階導數：

$$m'(x)=\beta_1+2\beta_2x$$

二階導數：

$$m''(x)=2\beta_2$$

-   $\beta_2>0$：向上凸；$\beta_2<0$：向下凹。
-   當 $\beta_2\ne0$，轉折點為 $x^*=-\beta_1/(2\beta_2)$。

## 2.4 Step 2｜估計與複雜度

令 $\mathbf Z=[\mathbf1,\mathbf X,\mathbf X^2,\ldots,\mathbf X^d]$：

$$\hat\beta=(\mathbf Z^\top\mathbf Z)^{-1}\mathbf Z^\top\mathbf Y$$

（需 $\mathbf Z$ 滿列秩）。

-   階數 $d$ 增加：訓練誤差通常不會增加。
-   但樣本外誤差可能上升（過度配適）。
-   階數應依研究目的與驗證表現選擇，**沒有通用的固定階數**。

## 2.5 適用情境與限制

| 適合                     | 不適合／應謹慎         |
|--------------------------|------------------------|
| 年齡與薪資等平滑彎曲趨勢 | 突然跳躍或局部複雜形狀 |
| 想保留可解釋的曲線形式   | 高階多項式振盪明顯     |
| 主要在觀測範圍內預測     | 大幅超出觀測範圍的外插 |

**優點：** 簡單、沿用 OLS。**限制：** 高階不穩定、全域形狀受限制。

# 3. Logistic Regression

## 3.1 資料與模型

對二元結果 $Y_i\in\{0,1\}$：

$$Y_i\mid\mathbf x_i\sim\operatorname{Bernoulli}(\pi_i),\quad\pi_i=P(Y_i=1\mid\mathbf x_i)$$

線性預測子：

$$\eta_i=\beta_0+\sum_{j=1}^{p}\beta_jX_{ij}$$

Logit 連結：

$$\log\frac{\pi_i}{1-\pi_i}=\eta_i$$

## 3.2 使用前提｜先檢查

| 條件               | 數學表述／判準                                      | 不成立時                         |
|------------------|---------------------------------|----------------------|
| 二元結果           | $Y_i\in\{0,1\}$                                     | 多類別或連續結果需其他模型       |
| Bernoulli 條件分布 | $Y_i\mid X_i\sim Bernoulli(\pi_i)$                  | 需重新考慮資料產生機制           |
| Logit 結構         | $\operatorname{logit}(\pi_i)=\mathbf x_i^\top\beta$ | 加非線性項／改連結               |
| 參數可識別         | 設計矩陣滿秩、無完全分離（有限 MLE）                | 可能無有限 MLE，需懲罰或特殊估計 |

若觀測彼此相關，**不能直接使用獨立樣本的傳統變異數公式**。

## 3.3 Step 1｜從 Logit 到機率

$$\log\frac{\pi_i}{1-\pi_i}=\eta_i$$

兩邊取指數：

$$\frac{\pi_i}{1-\pi_i}=e^{\eta_i}.$$

移項：

$$\pi_i=e^{\eta_i}(1-\pi_i)$$

得到：

$$\pi_i=\frac{e^{\eta_i}}{1+e^{\eta_i}}=\frac1{1+e^{-\eta_i}}$$

## 3.4 Step 2｜Bernoulli 概似函數

每筆資料的條件機率：

$$P(Y_i=y_i\mid\mathbf x_i)=\pi_i^{y_i}(1-\pi_i)^{1-y_i}.$$

假設條件獨立，聯合概似函數：

$$L(\beta)=\prod_{i=1}^{n}\pi_i^{y_i}(1-\pi_i)^{1-y_i}.$$

對數概似函數：

$$\ell(\beta)=\sum_{i=1}^{n}[y_i\log\pi_i+(1-y_i)\log(1-\pi_i)]$$

## 3.5 Step 3｜最大概似估計

將 $\pi_i=e^{\eta_i}/(1+e^{\eta_i})$ 代入：

$$\ell(\beta)=\sum_{i=1}^{n}\left[y_i\eta_i-\log(1+e^{\eta_i})\right]$$

Score function：

$$\frac{\partial\ell}{\partial\beta}=\mathbf X^\top(\mathbf Y-\boldsymbol\pi)$$

估計量滿足：

$$\mathbf X^\top(\mathbf Y-\hat{\boldsymbol\pi})=0$$

**通常沒有 OLS 式封閉解**，需數值最佳化。

## 3.6 Step 4｜勝算比（Odds Ratio）

固定其他解釋變數，$X_j$ 增加一單位：

$$\operatorname{logit}(\pi_{new})-\operatorname{logit}(\pi_{old})=\beta_j$$

因此：

$$OR_j=e^{\beta_j}$$

-   $OR_j=1$：勝算不變。
-   $OR_j>1$：勝算上升；$OR_j<1$：勝算下降。

## 3.7 適用情境與限制

| 適合                         | 不適合／應謹慎                 |
|------------------------------|--------------------------------|
| 是否購買、是否通過等二元事件 | 多類別結果直接套二元模型       |
| 需要事件機率或 OR 解釋       | 完全分離、稀少事件造成估計不穩 |

**優點：** 機率介於 0 與 1、係數可轉 OR。**限制：** 對模型形式與分離問題敏感。

# 4. Ridge Regression

## 4.1 資料、符號與前提

考慮連續結果的平方誤差模型，$\mathbf X$ 的 $p$ 個預測欄位已標準化；截距另外估計且不懲罰。

**需先檢查：**

-   平方誤差是否符合預測目的；若是二元結果，應考慮懲罰式 Logistic。
-   特徵尺度：懲罰項 $\sum_j\beta_j^2$ 依賴尺度，通常需標準化。
-   正則化能緩解共線性，但**不能修正內生性、嚴重模型錯置**。
-   $\lambda>0$ 時，即使 $p>n$，Ridge 仍可得到唯一的斜率估計（在此標準平方損失設定下）。

## 4.2 Step 1｜加入 L2 懲罰

令中心化的 $\mathbf Y$ 與 $\mathbf X$：

$$Q_R(\beta)=\|\mathbf Y-\mathbf X\beta\|_2^2+\lambda\|\beta\|_2^2$$

$$=\sum_{i=1}^n(Y_i-\mathbf x_i^\top\beta)^2+\lambda\sum_{j=1}^p\beta_j^2.$$

其中 $\lambda\ge0$：

-   $\lambda=0$：退回未懲罰的最小平方法。
-   $\lambda$ 越大：通常收縮越強。

## 4.3 Step 2｜推導 Ridge 解

對 $\beta$ 微分：

$$\nabla_\beta Q_R=-2\mathbf X^\top\mathbf Y+2\mathbf X^\top\mathbf X\beta+2\lambda\beta.$$

令其為零：

$$(\mathbf X^\top\mathbf X+\lambda\mathbf I_p)\hat\beta_R=\mathbf X^\top\mathbf Y.$$

因此當 $\lambda>0$：

$$\hat\beta_R=(\mathbf X^\top\mathbf X+\lambda\mathbf I_p)^{-1}\mathbf X^\top\mathbf Y$$

## 4.4 Step 3｜為什麼可以穩定估計？

令 $\mathbf X^\top\mathbf X$ 的特徵值為 $s_1,\ldots,s_p\ge0$。

加入 Ridge 後：

$$s_j\longrightarrow s_j+\lambda$$

只要 $\lambda>0$：

$$s_j+\lambda>0$$

因此矩陣可逆；原本接近 0 的特徵值不再導致相同程度的數值不穩定。

**代價：** 係數被收縮，通常產生偏誤。

## 4.5 適用情境與限制

| 適合                 | 不適合／應謹慎           |
|----------------------|--------------------------|
| 多個高度相關預測變數 | 需要自動刪除變數         |
| $p$ 相對於 $n$ 大    | 未標準化卻直接比較懲罰   |
| 重視預測穩定性       | 需要未懲罰係數的傳統推論 |

**優點：** 緩解共線性、控制變異。**限制：** 通常不會使係數精確為零。

# 5. Lasso Regression

## 5.1 資料、符號與前提

同樣考慮連續結果的平方誤差模型，預測欄位先標準化；截距不懲罰。

**需先檢查：**

-   研究目的是否允許使用稀疏模型（部分係數設為 0）。
-   高度相關的特徵可能使選擇結果不穩定。
-   $p>n$ 時仍可求得 Lasso 解，但**係數解不一定唯一**，需留意設計矩陣條件。

## 5.2 Step 1｜加入 L1 懲罰

$$Q_L(\beta)=\|\mathbf Y-\mathbf X\beta\|_2^2+\lambda\|\beta\|_1$$

$$=\sum_{i=1}^n(Y_i-\mathbf x_i^\top\beta)^2+\lambda\sum_{j=1}^p|\beta_j|.$$

比較：

$$\text{Ridge: }\sum_j\beta_j^2\qquad\text{Lasso: }\sum_j|\beta_j|.$$

L1 懲罰在 $\beta_j=0$ 不可微，因此可能得到**精確的零係數**。

## 5.3 Step 2｜一維 Lasso 的推導

考慮標準化後的一維問題：

$$Q(\beta)=(\beta-z)^2+\lambda|\beta|.$$

當 $\beta>0$：

$$2(\beta-z)+\lambda=0\Rightarrow\beta=z-\lambda/2.$$

當 $\beta<0$：

$$2(\beta-z)-\lambda=0\Rightarrow\beta=z+\lambda/2.$$

若 $|z|\le\lambda/2$，最佳解為 $\beta=0$。

## 5.4 Step 3｜Soft-thresholding

合併三種情況：

$$\hat\beta=\operatorname{sign}(z)(|z|-\lambda/2)_+$$

其中 $(a)_+=\max(a,0)$。

$$\hat\beta=\begin{cases}z-\lambda/2,&z>\lambda/2,\\0,&|z|\le\lambda/2,\\z+\lambda/2,&z<-\lambda/2.\end{cases}$$

**意義：** 小係數直接歸零；較大的係數往零收縮。此為一維示意，多變數問題需考慮變數之間的相關性。

## 5.5 適用情境與限制

| 適合                       | 不適合／應謹慎             |
|----------------------------|----------------------------|
| 預測變數很多、希望精簡     | 強烈相關變數造成選擇不穩   |
| 相信只有少數變數有主要訊號 | 所有變數都有微弱但真實效果 |

**優點：** 收縮與變數選擇。**限制：** 係數有偏、選模結果可能不穩定。

# 6. 模型比較與使用邊界

## 6.1 估計目標比較

| 方法       | 主要目標函數                                          |
|------------|-------------------------------------------------------|
| Linear     | $\min_\beta\|Y-X\beta\|_2^2$                          |
| Polynomial | $\min_\beta\|Y-Z_d\beta\|_2^2$                        |
| Logistic   | $\max_\beta\sum_i[y_i\eta_i-\log(1+e^{\eta_i})]$      |
| Ridge      | $\min_\beta\{\|Y-X\beta\|_2^2+\lambda\|\beta\|_2^2\}$ |
| Lasso      | $\min_\beta\{\|Y-X\beta\|_2^2+\lambda\|\beta\|_1\}$   |

*Ridge／Lasso 表中均採標準化資料與不懲罰截距的寫法。*

## 6.2 違反條件處理方式

| 發現問題       | 不應直接做的事                   | 合理方向                       |
|------------------|----------------------------|---------------------------|
| $Y$ 是二元事件 | 用一般 OLS 當機率模型            | Logistic                       |
| 條件平均有曲線 | 強迫只有 $X$ 的直線              | Polynomial 或其他非線性形式    |
| $X$ 完全共線   | 直接使用 OLS 反矩陣              | 刪除冗餘欄位、重參數化或正則化 |
| 異質變異       | 直接相信同質變異標準誤           | 穩健標準誤／重新建模           |
| 高相關特徵     | 將單一係數當作穩定效果           | Ridge；若需稀疏性可比較 Lasso  |
| 完全分離       | 直接相信普通 Logistic 有有限 MLE | 懲罰式／偏誤修正估計           |

# 參考文獻

-   James, G., Witten, D., Hastie, T., Tibshirani, R., & Taylor, J. (2023). An introduction to statistical learning: With applications in Python. Springer.
